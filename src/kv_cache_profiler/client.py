"""Profiled OpenAI-compatible SGLang client wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Iterable, Mapping, Protocol, Sequence
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

from .mlflow_integration import NoOpSpanSink
from .schema import RequestRecord, hash_messages, serialize_messages
from .storage import JSONLRequestWriter, PromptArtifactWriter


class ChatTransport(Protocol):
    def chat_completion(self, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Mapping[str, Any]:
        ...

    def stream_chat_completion(
        self,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> Iterable[Mapping[str, Any]]:
        ...


class OpenAICompatibleHTTPTransport:
    """Minimal stdlib transport for `/v1/chat/completions`."""

    def __init__(self, base_url: str, timeout_s: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def chat_completion(self, payload: Mapping[str, Any], headers: Mapping[str, str]) -> Mapping[str, Any]:
        body = json.dumps(dict(payload)).encode("utf-8")
        request = Request(self.chat_completions_url, data=body, headers=dict(headers), method="POST")
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"SGLang request failed with HTTP {exc.code}: {detail}") from exc

    def stream_chat_completion(
        self,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> Iterable[Mapping[str, Any]]:
        body = json.dumps(dict(payload)).encode("utf-8")
        request = Request(self.chat_completions_url, data=body, headers=dict(headers), method="POST")
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    yield json.loads(data)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"SGLang streaming request failed with HTTP {exc.code}: {detail}") from exc


@dataclass(slots=True)
class RequestContext:
    benchmark_run_id: str
    workflow_run_id: str
    thread_id: str
    agent_id: str
    previous_agent_id: str
    turn_id: int
    workflow_id: str = "kvflow-peer"
    workflow_type: str = "kvflow-peer"
    workflow_concurrency: int = 1
    experiment_name: str = "agent-specific-kv-cache-profiling"
    graph_node: str | None = None
    prompt_template_version: str = "kvflow-v1"
    chat_template_name: str = "openai-chat-json"


@dataclass(slots=True)
class ModelParameters:
    model: str = "profiler-model"
    temperature: float = 0.0
    max_tokens: int = 512
    stream: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }
        if self.stream:
            payload["stream_options"] = {"include_usage": True}
        payload.update(self.extra)
        return payload


@dataclass(slots=True)
class ProfiledChatResult:
    content: str
    request_uuid: str
    record: RequestRecord
    raw_response: Mapping[str, Any] | None = None


class ProfiledSGLangClient:
    """Shared model client used by all profiled workflow agent nodes."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:30000",
        api_key: str | None = None,
        model: str = "profiler-model",
        request_writer: JSONLRequestWriter | None = None,
        prompt_writer: PromptArtifactWriter | None = None,
        span_sink: Any | None = None,
        transport: ChatTransport | None = None,
        server_metrics_sampler: Any | None = None,
        timeout_s: float = 300.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.request_writer = request_writer
        self.prompt_writer = prompt_writer
        self.span_sink = span_sink or NoOpSpanSink()
        self.transport = transport or OpenAICompatibleHTTPTransport(base_url, timeout_s=timeout_s)
        self.server_metrics_sampler = server_metrics_sampler

    def chat(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        context: RequestContext,
        parameters: ModelParameters | None = None,
    ) -> ProfiledChatResult:
        parameters = parameters or ModelParameters(model=self.model)
        if parameters.model == "profiler-model" and self.model != "profiler-model":
            parameters = ModelParameters(
                model=self.model,
                temperature=parameters.temperature,
                max_tokens=parameters.max_tokens,
                stream=parameters.stream,
                extra=dict(parameters.extra),
            )

        request_uuid = str(uuid.uuid4())
        serialized_prompt = serialize_messages(messages)
        prompt_hash = hash_messages(messages)
        metadata = self._metadata(context, request_uuid)
        if self.prompt_writer is not None:
            self.prompt_writer.write(
                request_uuid=request_uuid,
                metadata=metadata,
                messages=messages,
                serialized_prompt=serialized_prompt,
            )

        payload = parameters.to_payload()
        payload["messages"] = list(messages)
        payload["metadata"] = metadata
        headers = self._headers(metadata)

        start_ns = time.perf_counter_ns()
        cache_before = self._sample_server_metrics()
        initial_span_attributes = {
            "benchmark.run_id": context.benchmark_run_id,
            "workflow.id": context.workflow_id,
            "workflow.run_id": context.workflow_run_id,
            "thread.id": context.thread_id,
            "agent.id": context.agent_id,
            "agent.previous_id": context.previous_agent_id,
            "agent.turn_id": context.turn_id,
            "request.uuid": request_uuid,
            "model.name": parameters.model,
            "model.temperature": parameters.temperature,
            "model.max_tokens": parameters.max_tokens,
            "prompt.template_version": context.prompt_template_version,
            "prompt.hash": prompt_hash,
        }

        with self.span_sink.span("sglang:chat-completion", initial_span_attributes) as span:
            try:
                if parameters.stream:
                    content, usage, response_id, first_token_ns, last_token_ns, raw_response = (
                        self._streaming_completion(payload, headers)
                    )
                else:
                    content, usage, response_id, first_token_ns, last_token_ns, raw_response = (
                        self._blocking_completion(payload, headers)
                    )
                end_ns = time.perf_counter_ns()
                cache_after = self._sample_server_metrics()
                record = self._build_record(
                    context=context,
                    request_uuid=request_uuid,
                    response_id=response_id,
                    parameters=parameters,
                    prompt_hash=prompt_hash,
                    usage=usage,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    first_token_ns=first_token_ns,
                    last_token_ns=last_token_ns,
                    cache_before=cache_before,
                    cache_after=cache_after,
                    status="ok",
                    error_type=None,
                )
                self._write_record(record)
                span.set_attributes(self._span_metrics(record))
                return ProfiledChatResult(
                    content=content,
                    request_uuid=request_uuid,
                    record=record,
                    raw_response=raw_response,
                )
            except Exception as exc:
                end_ns = time.perf_counter_ns()
                cache_after = self._sample_server_metrics()
                record = self._build_record(
                    context=context,
                    request_uuid=request_uuid,
                    response_id="",
                    parameters=parameters,
                    prompt_hash=prompt_hash,
                    usage={},
                    start_ns=start_ns,
                    end_ns=end_ns,
                    first_token_ns=None,
                    last_token_ns=None,
                    cache_before=cache_before,
                    cache_after=cache_after,
                    status="error",
                    error_type=exc.__class__.__name__,
                )
                self._write_record(record)
                span.set_attributes(self._span_metrics(record))
                raise

    def _blocking_completion(
        self,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> tuple[str, Mapping[str, Any], str, None, None, Mapping[str, Any]]:
        response = self.transport.chat_completion(payload, headers)
        choices = response.get("choices") or []
        content = ""
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
        usage = response.get("usage") or {}
        response_id = str(response.get("id") or "")
        return content, usage, response_id, None, None, response

    def _streaming_completion(
        self,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> tuple[str, Mapping[str, Any], str, int | None, int | None, Mapping[str, Any]]:
        content_parts: list[str] = []
        usage: Mapping[str, Any] = {}
        response_id = ""
        first_token_ns: int | None = None
        last_token_ns: int | None = None
        chunk_count = 0
        last_chunk: Mapping[str, Any] = {}

        for chunk in self.transport.stream_chat_completion(payload, headers):
            last_chunk = chunk
            response_id = response_id or str(chunk.get("id") or "")
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                token = delta.get("content")
                if token:
                    now_ns = time.perf_counter_ns()
                    if first_token_ns is None:
                        first_token_ns = now_ns
                    last_token_ns = now_ns
                    chunk_count += 1
                    content_parts.append(str(token))

        if not usage and chunk_count:
            usage = {"completion_tokens": chunk_count}
        return "".join(content_parts), usage, response_id, first_token_ns, last_token_ns, last_chunk

    def _build_record(
        self,
        *,
        context: RequestContext,
        request_uuid: str,
        response_id: str,
        parameters: ModelParameters,
        prompt_hash: str,
        usage: Mapping[str, Any],
        start_ns: int,
        end_ns: int,
        first_token_ns: int | None,
        last_token_ns: int | None,
        cache_before: Mapping[str, Any] | None,
        cache_after: Mapping[str, Any] | None,
        status: str,
        error_type: str | None,
    ) -> RequestRecord:
        prompt_tokens = _extract_int(usage, ("prompt_tokens", "input_tokens"))
        cached_tokens = _extract_cached_tokens(usage)
        output_tokens = _extract_int(usage, ("completion_tokens", "output_tokens", "generated_tokens"))
        return RequestRecord.build(
            benchmark_run_id=context.benchmark_run_id,
            experiment_name=context.experiment_name,
            workflow_id=context.workflow_id,
            workflow_run_id=context.workflow_run_id,
            workflow_type=context.workflow_type,
            thread_id=context.thread_id,
            workflow_concurrency=context.workflow_concurrency,
            agent_id=context.agent_id,
            previous_agent_id=context.previous_agent_id,
            turn_id=context.turn_id,
            graph_node=context.graph_node or context.agent_id,
            request_uuid=request_uuid,
            sglang_response_id=response_id,
            model_name=parameters.model,
            prompt_template_version=context.prompt_template_version,
            chat_template_name=context.chat_template_name,
            prompt_hash=prompt_hash,
            token_id_hash="",
            prompt_tokens=prompt_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            timestamp_start_ns=start_ns,
            timestamp_end_ns=end_ns,
            first_token_ns=first_token_ns,
            last_token_ns=last_token_ns,
            cache_used_tokens_before=_metric(cache_before, "cache_used_tokens"),
            cache_used_tokens_after=_metric(cache_after, "cache_used_tokens"),
            cache_utilization_before=_metric(cache_before, "cache_utilization"),
            cache_utilization_after=_metric(cache_after, "cache_utilization"),
            running_requests=_metric(cache_after, "running_requests"),
            queued_requests=_metric(cache_after, "queued_requests"),
            status=status,
            error_type=error_type,
        )

    def _write_record(self, record: RequestRecord) -> None:
        if self.request_writer is not None:
            self.request_writer.append(record)

    def _sample_server_metrics(self) -> Mapping[str, Any] | None:
        if self.server_metrics_sampler is None:
            return None
        return self.server_metrics_sampler.sample()

    def _metadata(self, context: RequestContext, request_uuid: str) -> dict[str, Any]:
        return {
            "benchmark_run_id": context.benchmark_run_id,
            "workflow_id": context.workflow_id,
            "workflow_run_id": context.workflow_run_id,
            "workflow_type": context.workflow_type,
            "thread_id": context.thread_id,
            "workflow_concurrency": context.workflow_concurrency,
            "agent_id": context.agent_id,
            "previous_agent_id": context.previous_agent_id,
            "turn_id": context.turn_id,
            "graph_node": context.graph_node or context.agent_id,
            "request_uuid": request_uuid,
        }

    def _headers(self, metadata: Mapping[str, Any]) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-UUID": str(metadata["request_uuid"]),
            "X-Workflow-ID": str(metadata["workflow_id"]),
            "X-Workflow-Run-ID": str(metadata["workflow_run_id"]),
            "X-Agent-ID": str(metadata["agent_id"]),
            "X-Turn-ID": str(metadata["turn_id"]),
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _span_metrics(self, record: RequestRecord) -> dict[str, Any]:
        return {
            "request.sglang_response_id": record.sglang_response_id,
            "prompt.tokens": record.prompt_tokens,
            "prompt.cached_tokens": record.cached_tokens,
            "prompt.new_prefill_tokens": record.new_prefill_tokens,
            "prompt.reported_cache_hit_ratio": record.reported_cache_hit_ratio,
            "output.tokens": record.output_tokens,
            "latency.ttft_ms": record.ttft_ms,
            "latency.tpot_ms": record.tpot_ms,
            "latency.e2e_ms": record.e2e_ms,
            "request.status": record.status,
            "request.error_type": record.error_type,
        }


def _metric(metrics: Mapping[str, Any] | None, key: str) -> Any:
    if not metrics:
        return None
    return metrics.get(key)


def _extract_int(usage: Mapping[str, Any], keys: Sequence[str]) -> int:
    for key in keys:
        value = usage.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _extract_cached_tokens(usage: Mapping[str, Any]) -> int:
    direct = _extract_int(
        usage,
        (
            "cached_tokens",
            "prompt_cached_tokens",
            "prompt_cache_hit_tokens",
            "cache_read_input_tokens",
        ),
    )
    if direct:
        return direct

    prompt_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    if isinstance(prompt_details, Mapping):
        nested = _extract_int(
            prompt_details,
            (
                "cached_tokens",
                "cache_read_tokens",
                "prompt_cache_hit_tokens",
            ),
        )
        if nested:
            return nested
    return 0

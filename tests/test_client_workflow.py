import json

from kv_cache_profiler.client import ProfiledSGLangClient
from kv_cache_profiler.storage import JSONLRequestWriter, PromptArtifactWriter, read_jsonl
from kv_cache_profiler.workflow import KVFLOW_AGENTS, KVFlowConfig, run_kvflow


class FakeTransport:
    def __init__(self):
        self.payloads = []
        self.headers = []

    def chat_completion(self, payload, headers):
        self.payloads.append(dict(payload))
        self.headers.append(dict(headers))
        metadata = payload["metadata"]
        agent_id = metadata["agent_id"]
        content = f"{agent_id} result"
        if agent_id == "reviewer":
            content = "APPROVED: complete"
        return {
            "id": f"chatcmpl-{metadata['request_uuid'][:8]}",
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 8,
                "prompt_tokens_details": {"cached_tokens": 25},
            },
        }

    def stream_chat_completion(self, payload, headers):
        response = self.chat_completion(payload, headers)
        content = response["choices"][0]["message"]["content"]
        for part in content.split(" "):
            yield {
                "id": response["id"],
                "choices": [{"delta": {"content": part + " "}}],
            }
        yield {"id": response["id"], "choices": [], "usage": response["usage"]}


def test_workflow_records_all_kvflow_agents(tmp_path):
    requests_path = tmp_path / "requests.jsonl"
    prompts_dir = tmp_path / "prompts"
    transport = FakeTransport()
    client = ProfiledSGLangClient(
        model="profiler-model",
        request_writer=JSONLRequestWriter(requests_path),
        prompt_writer=PromptArtifactWriter(prompts_dir),
        transport=transport,
    )
    config = KVFlowConfig(
        user_prompt="Build a small cache profiling report.",
        benchmark_run_id="bench",
        workflow_run_id="workflow-run",
        thread_id="thread",
        max_turns=1,
        use_langgraph=False,
    )

    final_state = run_kvflow(client, config)
    rows = read_jsonl(requests_path)

    assert final_state["previous_agent_id"] == "reviewer"
    assert [row["agent_id"] for row in rows] == list(KVFLOW_AGENTS)
    assert [row["previous_agent_id"] for row in rows] == ["START", "planner", "executor", "expresser"]
    assert all(row["workflow_run_id"] == "workflow-run" for row in rows)
    assert all(row["thread_id"] == "thread" for row in rows)
    assert all(row["turn_id"] == 1 for row in rows)
    assert len({row["request_uuid"] for row in rows}) == 4
    assert all(row["new_prefill_tokens"] == 75 for row in rows)
    assert all(row["reported_cache_hit_ratio"] == 0.25 for row in rows)
    assert all((prompts_dir / f"{row['request_uuid']}.json").exists() for row in rows)

    prompt_artifact = json.loads((prompts_dir / f"{rows[0]['request_uuid']}.json").read_text())
    assert prompt_artifact["contains_raw_prompts"] is True
    assert prompt_artifact["metadata"]["agent_id"] == "planner"

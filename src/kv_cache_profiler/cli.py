"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .analysis import write_analysis_outputs
from .client import ModelParameters, ProfiledSGLangClient
from .environment import collect_environment
from .mlflow_integration import initialize_mlflow
from .storage import JSONLRequestWriter, PromptArtifactWriter, export_jsonl_to_parquet, write_json
from .workflow import KVFlowConfig, run_kvflow


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_command(args)
    if args.command == "analyze":
        return _analyze_command(args)
    if args.command == "record-env":
        return _record_env_command(args)
    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kv-cache-profiler")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the KVFlow profiler workflow.")
    run_parser.add_argument("--prompt", required=True)
    run_parser.add_argument("--sglang-url", default="http://localhost:30000")
    run_parser.add_argument("--api-key")
    run_parser.add_argument("--model", default="profiler-model")
    run_parser.add_argument("--temperature", type=float, default=0.0)
    run_parser.add_argument("--max-tokens", type=int, default=512)
    run_parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=True)
    run_parser.add_argument("--max-turns", type=int, default=1)
    run_parser.add_argument("--benchmark-run-id", default="local-dev")
    run_parser.add_argument("--experiment-name", default="agent-specific-kv-cache-profiling")
    run_parser.add_argument("--workflow-id", default="kvflow-peer")
    run_parser.add_argument("--workflow-type", default="kvflow-peer")
    run_parser.add_argument("--workflow-run-id")
    run_parser.add_argument("--thread-id")
    run_parser.add_argument("--workflow-concurrency", type=int, default=1)
    run_parser.add_argument("--requests-jsonl", default="artifacts/requests.jsonl")
    run_parser.add_argument("--prompt-artifact-dir", default="artifacts/prompts")
    run_parser.add_argument("--mlflow-tracking-uri")
    run_parser.add_argument("--use-langgraph", action=argparse.BooleanOptionalAction, default=True)

    analyze_parser = subparsers.add_parser("analyze", help="Generate per-agent and transition summaries.")
    analyze_parser.add_argument("--requests-jsonl", required=True)
    analyze_parser.add_argument("--output-dir", default="artifacts/analysis")
    analyze_parser.add_argument("--parquet-output")

    env_parser = subparsers.add_parser("record-env", help="Record reproducibility environment metadata.")
    env_parser.add_argument("--output", default="artifacts/environment.json")

    return parser


def _run_command(args: argparse.Namespace) -> int:
    request_writer = JSONLRequestWriter(args.requests_jsonl)
    prompt_writer = PromptArtifactWriter(args.prompt_artifact_dir)
    span_sink = initialize_mlflow(
        tracking_uri=args.mlflow_tracking_uri,
        experiment_name=args.experiment_name,
    )
    client = ProfiledSGLangClient(
        base_url=args.sglang_url,
        api_key=args.api_key,
        model=args.model,
        request_writer=request_writer,
        prompt_writer=prompt_writer,
        span_sink=span_sink,
    )
    config = KVFlowConfig(
        user_prompt=args.prompt,
        benchmark_run_id=args.benchmark_run_id,
        experiment_name=args.experiment_name,
        workflow_id=args.workflow_id,
        workflow_type=args.workflow_type,
        workflow_run_id=args.workflow_run_id,
        thread_id=args.thread_id,
        workflow_concurrency=args.workflow_concurrency,
        max_turns=args.max_turns,
        use_langgraph=args.use_langgraph,
        model_parameters=ModelParameters(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            stream=args.stream,
        ),
    )
    final_state = run_kvflow(client, config)
    print(f"workflow_run_id={final_state['workflow_run_id']}")
    print(f"thread_id={final_state['thread_id']}")
    print(f"requests_jsonl={Path(args.requests_jsonl)}")
    return 0


def _analyze_command(args: argparse.Namespace) -> int:
    outputs = write_analysis_outputs(args.requests_jsonl, args.output_dir)
    if args.parquet_output:
        export_jsonl_to_parquet(args.requests_jsonl, args.parquet_output)
        outputs["parquet"] = Path(args.parquet_output)
    for name, path in outputs.items():
        print(f"{name}={path}")
    return 0


def _record_env_command(args: argparse.Namespace) -> int:
    write_json(args.output, collect_environment())
    print(f"environment={Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

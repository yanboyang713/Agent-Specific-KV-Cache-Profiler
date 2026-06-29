"""KVFlow / PEER-style workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import Any, Mapping, MutableMapping, TypedDict

from kv_cache_profiler.client import ModelParameters, ProfiledSGLangClient, RequestContext

KVFLOW_AGENTS = ("planner", "executor", "expresser", "reviewer")

SHARED_CONTEXT = """You are participating in a KVFlow profiling workflow.
The fixed workflow is planner -> executor -> expresser -> reviewer -> planner or END.
Keep responses concise and deterministic so cache measurements are reproducible."""

ROLE_PROMPTS = {
    "planner": "Role: planner. Decompose the user task, choose the next step, and incorporate reviewer feedback.",
    "executor": "Role: executor. Perform the planned work for the current step and report concrete results.",
    "expresser": "Role: expresser. Convert executor results into a clear user-facing response.",
    "reviewer": "Role: reviewer. Evaluate completeness. Start with APPROVED when complete, otherwise start with REVISE.",
}


class KVFlowState(TypedDict, total=False):
    benchmark_run_id: str
    workflow_id: str
    workflow_run_id: str
    workflow_type: str
    thread_id: str
    workflow_concurrency: int
    turn_id: int
    previous_agent_id: str
    user_prompt: str
    messages: list[dict[str, str]]
    planner_state: str
    executor_result: str
    expresser_output: str
    reviewer_feedback: str
    continue_workflow: bool
    max_turns: int


@dataclass(slots=True)
class KVFlowConfig:
    user_prompt: str
    benchmark_run_id: str = "local-dev"
    experiment_name: str = "agent-specific-kv-cache-profiling"
    workflow_id: str = "kvflow-peer"
    workflow_type: str = "kvflow-peer"
    workflow_run_id: str | None = None
    thread_id: str | None = None
    workflow_concurrency: int = 1
    max_turns: int = 1
    model_parameters: ModelParameters = field(default_factory=ModelParameters)
    use_langgraph: bool = True


def initial_state(config: KVFlowConfig) -> KVFlowState:
    return {
        "benchmark_run_id": config.benchmark_run_id,
        "workflow_id": config.workflow_id,
        "workflow_run_id": config.workflow_run_id or str(uuid.uuid4()),
        "workflow_type": config.workflow_type,
        "thread_id": config.thread_id or str(uuid.uuid4()),
        "workflow_concurrency": config.workflow_concurrency,
        "turn_id": 1,
        "previous_agent_id": "START",
        "user_prompt": config.user_prompt,
        "messages": [{"role": "user", "content": config.user_prompt}],
        "planner_state": "",
        "executor_result": "",
        "expresser_output": "",
        "reviewer_feedback": "",
        "continue_workflow": False,
        "max_turns": config.max_turns,
    }


def run_kvflow(client: ProfiledSGLangClient, config: KVFlowConfig) -> KVFlowState:
    state = initial_state(config)
    if config.use_langgraph:
        graph = _build_langgraph(client, config)
        return graph.invoke(state, config={"configurable": {"thread_id": state["thread_id"]}})
    return _run_local_state_machine(client, config, state)


def _run_local_state_machine(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
) -> KVFlowState:
    while True:
        state = _planner_node(client, config, state)
        state = _executor_node(client, config, state)
        state = _expresser_node(client, config, state)
        state = _reviewer_node(client, config, state)
        if not state.get("continue_workflow"):
            return state


def _build_langgraph(client: ProfiledSGLangClient, config: KVFlowConfig) -> Any:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is required for production profiler runs") from exc

    graph = StateGraph(KVFlowState)
    graph.add_node("planner", lambda state: _planner_node(client, config, state))
    graph.add_node("executor", lambda state: _executor_node(client, config, state))
    graph.add_node("expresser", lambda state: _expresser_node(client, config, state))
    graph.add_node("reviewer", lambda state: _reviewer_node(client, config, state))
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "expresser")
    graph.add_edge("expresser", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        lambda state: "planner" if state.get("continue_workflow") else END,
        {"planner": "planner", END: END},
    )
    return graph.compile()


def _planner_node(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
) -> KVFlowState:
    result = _call_agent(client, config, state, "planner")
    next_state = _copy_state(state)
    next_state["planner_state"] = result
    _append_agent_message(next_state, "planner", result)
    next_state["previous_agent_id"] = "planner"
    return next_state


def _executor_node(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
) -> KVFlowState:
    result = _call_agent(client, config, state, "executor")
    next_state = _copy_state(state)
    next_state["executor_result"] = result
    _append_agent_message(next_state, "executor", result)
    next_state["previous_agent_id"] = "executor"
    return next_state


def _expresser_node(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
) -> KVFlowState:
    result = _call_agent(client, config, state, "expresser")
    next_state = _copy_state(state)
    next_state["expresser_output"] = result
    _append_agent_message(next_state, "expresser", result)
    next_state["previous_agent_id"] = "expresser"
    return next_state


def _reviewer_node(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
) -> KVFlowState:
    result = _call_agent(client, config, state, "reviewer")
    next_state = _copy_state(state)
    next_state["reviewer_feedback"] = result
    _append_agent_message(next_state, "reviewer", result)
    approved = result.strip().upper().startswith("APPROVED")
    can_continue = int(next_state["turn_id"]) < int(next_state["max_turns"])
    next_state["continue_workflow"] = (not approved) and can_continue
    next_state["previous_agent_id"] = "reviewer"
    if next_state["continue_workflow"]:
        next_state["turn_id"] = int(next_state["turn_id"]) + 1
    return next_state


def _call_agent(
    client: ProfiledSGLangClient,
    config: KVFlowConfig,
    state: KVFlowState,
    agent_id: str,
) -> str:
    context = RequestContext(
        benchmark_run_id=str(state["benchmark_run_id"]),
        experiment_name=config.experiment_name,
        workflow_id=str(state["workflow_id"]),
        workflow_run_id=str(state["workflow_run_id"]),
        workflow_type=str(state["workflow_type"]),
        thread_id=str(state["thread_id"]),
        workflow_concurrency=int(state["workflow_concurrency"]),
        agent_id=agent_id,
        previous_agent_id=str(state["previous_agent_id"]),
        turn_id=int(state["turn_id"]),
        graph_node=agent_id,
    )
    messages = build_agent_messages(agent_id, state)
    result = client.chat(messages=messages, context=context, parameters=config.model_parameters)
    return result.content


def build_agent_messages(agent_id: str, state: Mapping[str, Any]) -> list[dict[str, str]]:
    if agent_id not in ROLE_PROMPTS:
        raise ValueError(f"Unknown KVFlow agent: {agent_id}")

    state_block = _state_block_for_agent(agent_id, state)
    return [
        {"role": "system", "content": SHARED_CONTEXT},
        {"role": "system", "content": ROLE_PROMPTS[agent_id]},
        {
            "role": "user",
            "content": (
                f"Original user task:\n{state.get('user_prompt', '')}\n\n"
                f"Workflow turn: {state.get('turn_id', 1)}\n\n"
                f"{state_block}"
            ),
        },
    ]


def _state_block_for_agent(agent_id: str, state: Mapping[str, Any]) -> str:
    if agent_id == "planner":
        feedback = state.get("reviewer_feedback") or "No reviewer feedback yet."
        return f"Reviewer feedback:\n{feedback}\n\nCreate or update the plan."
    if agent_id == "executor":
        return f"Current planner state:\n{state.get('planner_state') or 'No plan recorded.'}\n\nExecute the current step."
    if agent_id == "expresser":
        return f"Executor result:\n{state.get('executor_result') or 'No executor result recorded.'}\n\nExpress the result clearly."
    if agent_id == "reviewer":
        return f"Expresser output:\n{state.get('expresser_output') or 'No expressed output recorded.'}\n\nReview the output."
    raise ValueError(f"Unknown KVFlow agent: {agent_id}")


def _append_agent_message(state: MutableMapping[str, Any], agent_id: str, content: str) -> None:
    messages = list(state.get("messages") or [])
    messages.append({"role": "assistant", "name": agent_id, "content": content})
    state["messages"] = messages


def _copy_state(state: Mapping[str, Any]) -> KVFlowState:
    copied = dict(state)
    copied["messages"] = list(state.get("messages") or [])
    return copied  # type: ignore[return-value]

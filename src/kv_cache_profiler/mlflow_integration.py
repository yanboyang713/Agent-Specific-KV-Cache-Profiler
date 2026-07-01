"""MLflow tracing adapter."""

from __future__ import annotations

from contextlib import contextmanager
from importlib.util import find_spec
import warnings
from typing import Any, Iterator, Mapping


class SpanHandle:
    def set_attributes(self, attributes: Mapping[str, Any]) -> None:
        return None


class NoOpSpanSink:
    @contextmanager
    def span(self, name: str, attributes: Mapping[str, Any]) -> Iterator[SpanHandle]:
        del name, attributes
        yield SpanHandle()


class _MLflowSpanHandle(SpanHandle):
    def __init__(self, span: Any) -> None:
        self.span = span

    def set_attributes(self, attributes: Mapping[str, Any]) -> None:
        for key, value in attributes.items():
            if value is None:
                continue
            if hasattr(self.span, "set_attribute"):
                self.span.set_attribute(key, value)
            elif hasattr(self.span, "set_attributes"):
                self.span.set_attributes({key: value})


class MLflowSpanSink:
    def __init__(self, mlflow_module: Any) -> None:
        self.mlflow = mlflow_module

    @contextmanager
    def span(self, name: str, attributes: Mapping[str, Any]) -> Iterator[SpanHandle]:
        start_span = getattr(self.mlflow, "start_span", None)
        if not callable(start_span):
            yield SpanHandle()
            return

        with start_span(name=name) as span:
            handle = _MLflowSpanHandle(span)
            handle.set_attributes(attributes)
            yield handle


def initialize_mlflow(
    *,
    tracking_uri: str | None,
    experiment_name: str,
    enable_langchain_autolog: bool = True,
) -> MLflowSpanSink:
    import mlflow

    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    if enable_langchain_autolog:
        langchain = getattr(mlflow, "langchain", None)
        autolog = getattr(langchain, "autolog", None) if langchain is not None else None
        if callable(autolog) and find_spec("langchain") is not None:
            autolog()
        else:
            warnings.warn(
                "MLflow LangChain autologging is unavailable because langchain is not installed; "
                "continuing with explicit profiler spans.",
                RuntimeWarning,
                stacklevel=2,
            )
    return MLflowSpanSink(mlflow)

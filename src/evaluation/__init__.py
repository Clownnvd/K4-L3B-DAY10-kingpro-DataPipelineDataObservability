"""Evaluation exports loaded on demand, so testset construction stays lightweight."""
from importlib import import_module

def __getattr__(name):
    module = {"EvaluationBundle": "metrics", "JudgeVerdict": "metrics",
              "evaluate_pipeline": "metrics", "build_test_set": "testset"}.get(name)
    if module is None:
        raise AttributeError(name)
    return getattr(import_module(f".{module}", __name__), name)

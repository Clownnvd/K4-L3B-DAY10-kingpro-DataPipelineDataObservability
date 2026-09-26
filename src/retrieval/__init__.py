"""Load provider/model dependencies only when their exports are requested."""
from importlib import import_module

def __getattr__(name):
    module = {"build_agent": "agent", "run_agent_question": "agent",
              "MiniLMEmbeddings": "embeddings", "LocalEmbeddingIndex": "index",
              "SearchResult": "index", "build_llm": "llm", "AnswerResult": "qa",
              "answer_question": "qa"}.get(name)
    if module is None:
        raise AttributeError(name)
    return getattr(import_module(f".{module}", __name__), name)

# Patch langchain_core Reviver to match langgraph expectations before importing langgraph
try:
    from langchain_core.load.load import Reviver
    _orig_init = Reviver.__init__
    def _patched_init(self, *args, **kwargs):
        kwargs.pop("allowed_objects", None)
        return _orig_init(self, *args, **kwargs)
    Reviver.__init__ = _patched_init
except Exception:
    pass

# Patch langchain root module to have missing attributes accessed by langchain_core globals
try:
    import langchain
    if not hasattr(langchain, "verbose"):
        langchain.verbose = False
    if not hasattr(langchain, "debug"):
        langchain.debug = False
    if not hasattr(langchain, "llm_cache"):
        langchain.llm_cache = None
except Exception:
    pass

# Patch langgraph copy_checkpoint and empty_checkpoint to avoid KeyError: '__start__'
try:
    import langgraph.checkpoint.base as lg_base

    class SafeVersionsSeen(dict):
        def __getitem__(self, key):
            if key not in self:
                self[key] = {}
            return super().__getitem__(key)

        def copy(self):
            return SafeVersionsSeen({k: v.copy() for k, v in self.items()})

    _orig_copy = lg_base.copy_checkpoint
    def patched_copy(checkpoint):
        copied = _orig_copy(checkpoint)
        copied["versions_seen"] = SafeVersionsSeen(copied["versions_seen"])
        return copied
    lg_base.copy_checkpoint = patched_copy

    _orig_empty = lg_base.empty_checkpoint
    def patched_empty():
        empty_cp = _orig_empty()
        empty_cp["versions_seen"] = SafeVersionsSeen(empty_cp["versions_seen"])
        return empty_cp
    lg_base.empty_checkpoint = patched_empty
except Exception:
    pass

from app.agents.state import AgentState
from app.agents.graph import graph

__all__ = ["AgentState", "graph"]

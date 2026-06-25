from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import PipelineState

_state: PipelineState | None = None
_memories: dict[str, BaseMemory] | None = None


def get_state() -> PipelineState:
    global _state
    if _state is None:
        _state = PipelineState()
    return _state


def get_memory(agent_name: str) -> BaseMemory:
    global _memories
    if _memories is None:
        _memories = {}
    if agent_name not in _memories:
        _memories[agent_name] = ConversationMemory()
    return _memories[agent_name]


def reset_state() -> PipelineState:
    global _state, _memories
    _state = PipelineState()
    _memories = {}
    return _state

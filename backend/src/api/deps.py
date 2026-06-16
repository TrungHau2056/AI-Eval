from src.models.schemas import PipelineState

_state: PipelineState | None = None


def get_state() -> PipelineState:
    global _state
    if _state is None:
        _state = PipelineState()
    return _state


def reset_state() -> PipelineState:
    global _state
    _state = PipelineState()
    return _state

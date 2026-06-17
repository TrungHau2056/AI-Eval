from typing import Any

from src.memory.base import BaseMemory


class ConversationMemory(BaseMemory):
    def __init__(self):
        self._history: list[dict[str, Any]] = []

    def add(self, role: str, content: Any) -> None:
        self._history.append({"role": role, "content": content})

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_context(self, max_entries: int = 0) -> str:
        entries = self._history[-max_entries:] if max_entries else self._history
        if not entries:
            return ""
        lines: list[str] = []
        for entry in entries:
            role = entry["role"]
            content = entry["content"]
            if role == "user":
                lines.append(f"[User guidance]: {content}")
            elif role == "assistant":
                lines.append(f"[Kết quả trước]: {content}")
            elif role == "feedback":
                lines.append(f"[Feedback]: {content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._history.clear()

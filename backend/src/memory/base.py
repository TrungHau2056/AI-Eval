from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    @abstractmethod
    def add(self, role: str, content: Any) -> None:
        """Thêm 1 entry vào memory (role: 'user' | 'assistant' | 'feedback')."""
        ...

    @abstractmethod
    def get_history(self) -> list[dict[str, Any]]:
        """Trả về toàn bộ lịch sử."""
        ...

    @abstractmethod
    def get_context(self, max_entries: int = 0) -> str:
        """Trả về context dạng text để đưa vào prompt. max_entries=0 nghĩa là lấy tất cả."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Xóa toàn bộ memory."""
        ...

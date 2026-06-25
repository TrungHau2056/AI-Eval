from abc import ABC, abstractmethod
from src.models.schemas import RawInput


class DataIngestion(ABC):
    @abstractmethod
    def load(self) -> RawInput: ...

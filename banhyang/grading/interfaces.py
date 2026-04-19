from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseLLMService(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, schema: Optional[Any] = None) -> dict:
        """
        프롬프트와 (선택적으로) 응답 스키마를 받아 딕셔너리를 반환합니다.
        """
        pass
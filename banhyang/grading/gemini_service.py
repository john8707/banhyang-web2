from .interfaces import BaseLLMService
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
import os


class GeminiLLMService(BaseLLMService):
    def __init__(self, model_name="gemini-3.1-pro-preview"):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = model_name

    def generate_response(self, prompt: str, schema: type[BaseModel] = None):
        config_kwargs = {
            "temperature" : 0.2,
        }
        if schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema
        
        config = types.GenerateContentConfig(**config_kwargs)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )
            if schema:
                return response.parsed.model_dump()
            else:
                return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "JSON 파싱 실패", "raw": response.text}
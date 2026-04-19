from pydantic import BaseModel, Field
from typing import List
from .interfaces import BaseLLMService

# 1. 요약/번역을 위한 데이터 강제 스키마
class SummaryOutput(BaseModel):
    author_name: str = Field(description="에세이 작성자의 이름 (텍스트에서 찾을 수 없으면 'Unknown'으로 표기)")
    translation: str = Field(description="전체 영문 에세이의 매끄러운 한국어 번역본")
    summary: List[str] = Field(description="핵심 내용을 3줄로 요약한 리스트")

# 2. 채점을 위한 데이터 강제 스키마
class ScoringOutput(BaseModel):
    score: int = Field(description="100, 95, 90, 85 중 하나의 점수만 부여")
    reasoning: str = Field(description="점수를 부여한 상세한 이유 (한국어)")

class EssayGrader:
    def __init__(self, llm_service_translate: BaseLLMService, llm_service_scoring: BaseLLMService):
        self.llm_translate = llm_service_translate
        self.llm_scoring = llm_service_scoring

    def extract_info_and_translate(self, title: str, text: str) -> dict:
        # Step 1: 번역 및 요약 (Summary LLM)
        summary_prompt = f"에세이의 작성자의 이름을 찾아내고, 에세이 전체를 한국어로 번역하고(원본), 핵심 내용을 3줄로 요약해주세요.\n\n제목: {title} \n\n에세이: {text}"
        
        print("번역 및 요약 진행 중...")
        summary_result = self.llm_translate.generate_response(
            prompt=summary_prompt, 
            schema=SummaryOutput # 스키마 주입
        )

        return summary_result
    
    def evaluate_score(self, text: str, criteria: str) -> dict:
        # Step 2: 엄격한 채점 (Scoring LLM)
        scoring_prompt = f"""
        당신은 엄격하고 공정한 대학원 조교입니다. 다음 에세이를 읽고 아래 채점 기준에 따라 평가하세요.
        
        [채점 기준]
        {criteria}
        
        에세이: {text}
        """
        
        print("채점 진행 중...")
        scoring_result = self.llm_scoring.generate_response(
            prompt=scoring_prompt, 
            schema=ScoringOutput # 스키마 주입
        )

        return scoring_result

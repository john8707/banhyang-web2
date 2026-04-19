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
    score: str = Field(description="평가 기준에 따라 부여된 최종 점수 또는 등급")
    reasoning: str = Field(description="점수를 부여한 상세한 이유 (한국어)")

class EssayGrader:
    def __init__(self, llm_service_translate: BaseLLMService, llm_service_scoring: BaseLLMService):
        self.llm_translate = llm_service_translate
        self.llm_scoring = llm_service_scoring

    def extract_info_and_translate(self, title: str, text: str) -> dict:
        # Step 1: 번역 및 요약 (Summary LLM)
        summary_prompt = f"""
        에세이의 작성자의 이름을 찾아내고, 에세이 전체를 한국어로 번역하고(원본), 핵심 내용을 3줄로 요약해주세요.
        제목: {title}
        에세이: {text}
        """
        
        print("번역 및 요약 진행 중...")
        summary_result = self.llm_translate.generate_response(
            prompt=summary_prompt, 
            schema=SummaryOutput # 스키마 주입
        )

        return summary_result
    
    def evaluate_score(self, text: str, criteria: str, score_range: str, strictness: str) -> dict:
        # Step 2: 엄격한 채점 (Scoring LLM)
        scoring_prompt = f"""
        당신은 엄격하고 공정한 대학원 조교입니다. 다음 설정된 평가 지침에 따라 에세이를 분석하고 채점하세요.
        [평가 설정]
        - 채점 강도 : {strictness}
        - 점수 부여 규칙 : {score_range}

        [상세 채점 기준]
        {criteria}
        
        에세이: {text}
        """
        
        print("채점 진행 중...")
        scoring_result = self.llm_scoring.generate_response(
            prompt=scoring_prompt, 
            schema=ScoringOutput # 스키마 주입
        )

        return scoring_result

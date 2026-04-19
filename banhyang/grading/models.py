# scoring/models.py
from django.db import models

class GoogleOAuthToken(models.Model):
    """구글 OAuth 토큰을 저장하는 싱글톤(Singleton) 모델"""
    email = models.EmailField(primary_key=True, help_text="구글 계정 이메일")
    token_json = models.TextField(help_text="구글 인증 토큰 JSON 데이터")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} (Last Updated: {self.updated_at})"
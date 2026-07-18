from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    debug: bool = False

    naver_client_id: str
    naver_client_secret: str

    anthropic_api_key: str
    openai_api_key: str

    serp_api_key: str = ""
    youtube_api_key: str = ""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    auth_password: str = ""
    session_ttl_seconds: int = 3600

    env: str = "local"

    cors_allowed_frontend_url: str = "http://localhost:3000"

    kakao_client_id: str
    kakao_redirect_uri: str

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:33333/api/v1/google-authentication/request-access-token-after-redirection"

    open_dart_api_key: str = ""

    langchain_api_key: str = ""
    langchain_project: str = "disclosure-analysis"
    langchain_tracing_v2: bool = False

    analysis_api_finance_url: Optional[str] = None
    analysis_api_timeout_seconds: float = 10.0
    openai_finance_agent_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    finance_rag_top_k: int = 3
    finance_analysis_cache_ttl_seconds: int = 3600
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "stock-supporters-backend"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    dart_api_key: str = ""

    multi_agent_model: str = "gpt-4.1-nano"
    multi_agent_temperature: float = 0.2
    multi_agent_max_tokens: int = 1024
    multi_agent_request_timeout: float = 30.0
    multi_agent_max_steps: int = 6

    ddakjubu_llm_model: str = "gpt-5-mini"
    ddakjubu_md_path: str = "ddakjubu.md"

    ddakjubu2_llm_model: str = "gpt-5-mini"
    ddakjubu2_md_path: str = "ddakjubu2.md"
    ddakjubu2_enhanced_md_path: str = "ddakjubu2_enhanced.md"
    # 자막 포함 재학습 시 영상 간 대기 (초). IP 차단을 피하기 위해 느리게 진행.
    ddakjubu2_enhance_sleep_seconds: int = 600
    ddakjubu2_enhance_published_after_iso: str = "2026-01-01T00:00:00+00:00"
    # 매일 학습 잡에서 자막 조회 시 영상 간 대기 (일일 1~3편이라 짧게)
    ddakjubu2_daily_transcript_sleep_seconds: int = 120
    # 방법론 적용 분석 결과 Redis 캐시 TTL
    ddakjubu2_apply_cache_ttl_seconds: int = 21600
    # 마스터 방법론 병합 시 사용할 최근 영상 방법론 수
    ddakjubu2_master_merge_max_videos: int = 50
    # 방법론 적용 분석 LLM reasoning effort (minimal | low | medium)
    ddakjubu2_apply_reasoning_effort: str = "low"

    # YouTube 자막 IP 차단 우회용 프록시 설정
    # 아래 중 우선순위: Webshare → Generic HTTP/HTTPS → 미사용(직결)
    youtube_proxy_webshare_username: str = ""
    youtube_proxy_webshare_password: str = ""
    youtube_proxy_http_url: str = ""
    youtube_proxy_https_url: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()

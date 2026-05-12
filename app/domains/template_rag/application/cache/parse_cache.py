"""양식/raw 파싱 결과 디스크 영속 캐시.

key 예: 'template_parse:<form_type>:<file_hash>'
저장 위치: <project>/parse_cache/<sha256(key)>.json
- 서버 재시작/배포에도 유지
- 양식이 같은 파일(file_hash 일치) 이면 ingest 1회 LLM 호출 후 PPT 생성 단계는 무비용
"""
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 프로젝트 루트 추정: 이 파일 기준 4단계 위 (app/domains/template_rag/application/cache -> repo root)
_CACHE_DIR = Path(__file__).resolve().parents[5] / "parse_cache"


class ParseCache:
    """디스크 파일(JSON) 기반 영속 캐시.

    in-memory 호환 인터페이스 유지: get / set / keys / clear
    """

    @classmethod
    def _ensure_dir(cls) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("[ParseCache] cache dir 생성 실패: %s", e)

    @classmethod
    def _path_for(cls, key: str) -> Path:
        safe = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return _CACHE_DIR / f"{safe}.json"

    @classmethod
    def get(cls, key: str) -> dict[str, Any] | None:
        cls._ensure_dir()
        path = cls._path_for(key)
        if not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("[ParseCache] read 실패 (%s): %s", path.name, e)
            return None

    @classmethod
    def set(cls, key: str, value: dict[str, Any]) -> None:
        cls._ensure_dir()
        path = cls._path_for(key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        except Exception as e:
            logger.warning("[ParseCache] write 실패 (%s): %s", path.name, e)

    @classmethod
    def keys(cls) -> list[str]:
        cls._ensure_dir()
        return [p.stem for p in _CACHE_DIR.glob("*.json")]

    @classmethod
    def clear(cls) -> None:
        if _CACHE_DIR.is_dir():
            for p in _CACHE_DIR.glob("*.json"):
                try:
                    p.unlink()
                except Exception:
                    pass

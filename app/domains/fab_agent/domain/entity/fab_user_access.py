from dataclasses import dataclass, field
from typing import List


@dataclass
class FabUserAccess:
    """사용자별 데이터 접근 권한 (RBAC/RLS 근거).

    clearance_grade: 조회 가능한 최대 보안등급 (1=일반, 2=대외비, 3=극비)
    modules: 접근 가능한 공정 모듈 목록 (COMMON 은 항상 허용)
    """

    account_email: str
    clearance_grade: int
    modules: List[str] = field(default_factory=list)
    is_admin: bool = False

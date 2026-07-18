from typing import Optional

from app.domains.ddakjubu2.application.port.methodology_merge_port import (
    MethodologyMergePort,
)
from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.application.response.learning_note_response import (
    MasterMethodologyResponse,
)
from app.domains.ddakjubu2.application.usecase.get_learning_note_detail_usecase import (
    methodology_to_dto,
)


class RebuildMasterMethodologyUseCase:
    """최근 N개 영상 방법론을 LLM 으로 통합해 마스터 방법론 새 버전을 생성한다."""

    def __init__(
        self,
        methodology_repository_port: MethodologyRepositoryPort,
        methodology_merge_port: MethodologyMergePort,
        max_videos: int = 50,
    ):
        self._methodology_repository_port = methodology_repository_port
        self._methodology_merge_port = methodology_merge_port
        self._max_videos = max_videos

    async def execute(self) -> Optional[MasterMethodologyResponse]:
        recent = await self._methodology_repository_port.find_recent(
            limit=self._max_videos
        )
        # 방법론이 드러나지 않은 영상(analysis_steps 빈 배열)은 병합 대상에서 제외
        candidates = [m for m in recent if not m.is_empty()]
        print(
            f"[ddakjubu2_master] 병합 대상 방법론 {len(candidates)}개 "
            f"(최근 {len(recent)}개 중)",
            flush=True,
        )
        if not candidates:
            print("[ddakjubu2_master] 병합할 방법론이 없습니다.", flush=True)
            return None

        master = await self._methodology_merge_port.merge(candidates)
        if master.is_empty():
            print("[ddakjubu2_master] 병합 결과가 비어 있어 저장하지 않습니다.", flush=True)
            return None

        version = await self._methodology_repository_port.save_master(
            master, source_video_count=len(candidates)
        )
        print(f"[ddakjubu2_master] 마스터 방법론 v{version} 저장 완료", flush=True)
        return MasterMethodologyResponse(
            version=version, methodology=methodology_to_dto(master)
        )

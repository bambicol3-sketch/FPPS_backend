from app.domains.google_auth.application.port.out.google_user_info_port import GoogleUserInfoPort
from app.domains.google_auth.application.response.google_user_info_response import GoogleUserInfoResponse


class GetGoogleUserInfoUseCase:
    def __init__(self, google_user_info_port: GoogleUserInfoPort):
        self._port = google_user_info_port

    async def execute(self, access_token: str) -> GoogleUserInfoResponse:
        user_info = await self._port.fetch_user_info(access_token)
        return GoogleUserInfoResponse(
            google_id=user_info.google_id,
            nickname=user_info.nickname,
            email=user_info.email,
        )

import httpx

from app.domains.google_auth.application.port.out.google_user_info_port import GoogleUserInfoPort
from app.domains.google_auth.domain.entity.google_user_info import GoogleUserInfo

GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleUserInfoClient(GoogleUserInfoPort):

    async def fetch_user_info(self, access_token: str) -> GoogleUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code != 200:
            body = response.json()
            error_desc = body.get("error_description") or body.get("error", "Google 사용자 정보 조회 실패")
            raise ValueError(error_desc)

        body = response.json()
        return GoogleUserInfo(
            google_id=body["sub"],
            nickname=body.get("name"),
            email=body.get("email"),
        )

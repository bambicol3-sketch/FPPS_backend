import httpx

from app.domains.google_auth.application.port.out.google_token_port import GoogleTokenPort
from app.domains.google_auth.domain.entity.google_token import GoogleToken

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleTokenClient(GoogleTokenPort):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    async def fetch_token(self, code: str) -> GoogleToken:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "code": code,
                },
            )

        if response.status_code != 200:
            body = response.json()
            error_desc = body.get("error_description", "Google 토큰 발급 실패")
            raise ValueError(error_desc)

        body = response.json()
        return GoogleToken(
            access_token=body["access_token"],
            token_type=body["token_type"],
            expires_in=body["expires_in"],
            refresh_token=body.get("refresh_token"),
            scope=body.get("scope"),
            id_token=body.get("id_token"),
        )

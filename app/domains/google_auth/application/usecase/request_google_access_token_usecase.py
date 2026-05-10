from app.domains.google_auth.application.port.out.google_token_port import GoogleTokenPort
from app.domains.google_auth.application.response.google_token_response import GoogleTokenResponse


class RequestGoogleAccessTokenUseCase:
    def __init__(self, google_token_port: GoogleTokenPort):
        self._port = google_token_port

    async def execute(self, code: str) -> GoogleTokenResponse:
        token = await self._port.fetch_token(code)
        return GoogleTokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            refresh_token=token.refresh_token,
            scope=token.scope,
            id_token=token.id_token,
        )

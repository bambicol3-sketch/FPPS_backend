from app.domains.google_auth.domain.value_object.google_oauth_url import GoogleOAuthUrl


class GenerateGoogleOAuthUrlUseCase:
    def __init__(self, client_id: str, redirect_uri: str):
        self._client_id = client_id
        self._redirect_uri = redirect_uri

    def execute(self) -> str:
        return GoogleOAuthUrl(self._client_id, self._redirect_uri).value

from urllib.parse import urlencode

GOOGLE_AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"


class GoogleOAuthUrl:
    def __init__(self, client_id: str, redirect_uri: str):
        if not client_id:
            raise ValueError("google_client_id는 필수입니다.")
        if not redirect_uri:
            raise ValueError("google_redirect_uri는 필수입니다.")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        self._url = f"{GOOGLE_AUTH_BASE_URL}?{urlencode(params)}"

    @property
    def value(self) -> str:
        return self._url

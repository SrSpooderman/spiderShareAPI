import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from jose import JWTError, jwt

from app.modules.auth.application.oidc_login import OidcAuthenticationError, OidcIdentity
from config.settings import settings


class KeycloakOidcProvider:
    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        authorization_endpoint = _authorization_endpoint()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": _required(settings.oidc_client_id, "OIDC_CLIENT_ID"),
                "redirect_uri": redirect_uri,
                "scope": settings.oidc_scope,
                "state": state,
            }
        )
        return f"{authorization_endpoint}?{query}"

    def authenticate(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        tokens = self._exchange_code(code=code, redirect_uri=redirect_uri)
        token = tokens.get("id_token") or tokens.get("access_token")
        if not isinstance(token, str) or not token:
            raise OidcAuthenticationError("OIDC token response did not include a JWT")

        claims = self._decode_token(token)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise OidcAuthenticationError("OIDC token did not include a subject")

        return OidcIdentity(
            subject=subject,
            name=_optional_string(claims.get("name")),
            email=_optional_string(claims.get("email")),
            groups=_groups_from_claims(claims),
        )

    def _exchange_code(self, *, code: str, redirect_uri: str) -> dict[str, Any]:
        data = urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": _required(settings.oidc_client_id, "OIDC_CLIENT_ID"),
                "client_secret": _required(settings.oidc_client_secret, "OIDC_CLIENT_SECRET"),
            }
        ).encode("utf-8")
        request = Request(
            _token_endpoint(),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise OidcAuthenticationError("OIDC token exchange failed") from error

        if not isinstance(payload, dict):
            raise OidcAuthenticationError("OIDC token response was invalid")

        return payload

    def _decode_token(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            key = self._jwks_key(header.get("kid"))
            return jwt.decode(
                token,
                key,
                algorithms=[header.get("alg", "RS256")],
                audience=settings.oidc_client_id,
                issuer=_issuer_url(),
            )
        except JWTError as error:
            raise OidcAuthenticationError("OIDC token validation failed") from error

    def _jwks_key(self, kid: str | None) -> dict[str, Any]:
        try:
            with urlopen(_jwks_uri(), timeout=10) as response:
                jwks = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise OidcAuthenticationError("OIDC JWKS lookup failed") from error

        keys = jwks.get("keys") if isinstance(jwks, dict) else None
        if not isinstance(keys, list):
            raise OidcAuthenticationError("OIDC JWKS response was invalid")

        for key in keys:
            if isinstance(key, dict) and (kid is None or key.get("kid") == kid):
                return key

        raise OidcAuthenticationError("OIDC signing key was not found")


def _groups_from_claims(claims: dict[str, Any]) -> list[str]:
    groups = claims.get("groups", [])
    if not isinstance(groups, list):
        return []

    return [str(group) for group in groups if str(group).strip()]


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _required(value: str | None, name: str) -> str:
    if value is None or not value.strip():
        raise OidcAuthenticationError(f"{name} is not configured")
    return value


def _issuer_url() -> str:
    return _required(settings.oidc_issuer_url, "OIDC_ISSUER_URL").rstrip("/")


def _authorization_endpoint() -> str:
    if settings.oidc_authorization_endpoint:
        return settings.oidc_authorization_endpoint
    return f"{_issuer_url()}/protocol/openid-connect/auth"


def _token_endpoint() -> str:
    if settings.oidc_token_endpoint:
        return settings.oidc_token_endpoint
    return f"{_issuer_url()}/protocol/openid-connect/token"


def _jwks_uri() -> str:
    if settings.oidc_jwks_uri:
        return settings.oidc_jwks_uri
    return f"{_issuer_url()}/protocol/openid-connect/certs"

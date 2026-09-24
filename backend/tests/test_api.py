from fastapi.testclient import TestClient

from app.main import app
from app.security import (
    access_token,
    decode_token,
    password_errors,
)


client = TestClient(app)


def test_health_endpoint_contract():
    """
    Verify that the public health endpoint exists and returns
    the expected API health contract.
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["api"] == "ok"
    assert "database" in data
    assert "redis" in data
    assert "search" in data
    assert "websocket" in data
    assert "version" in data
    assert "environment" in data
    assert "time" in data


def test_password_rules_endpoint():
    """
    Verify that the frontend can retrieve the server-side
    password policy.
    """
    response = client.get("/api/v1/auth/password-rules")

    assert response.status_code == 200

    data = response.json()

    assert "rules" in data
    assert isinstance(data["rules"], list)

    assert any("12 characters" in rule for rule in data["rules"])
    assert any("uppercase" in rule for rule in data["rules"])
    assert any("lowercase" in rule for rule in data["rules"])
    assert any("number" in rule for rule in data["rules"])
    assert any("symbol" in rule for rule in data["rules"])


def test_password_policy_rejects_weak_passwords():
    weak_passwords = [
        "",
        "password",
        "Password",
        "Password123",
        "password123!",
        "PASSWORD123!",
    ]

    for password in weak_passwords:
        assert password_errors(password)


def test_password_policy_accepts_strong_password():
    assert password_errors("ThreatLens!Demo1") == []


def test_access_token_round_trip():
    """
    Verify that an access token contains the expected claims
    and can be decoded using the configured JWT secret.
    """
    token = access_token(
        user_id="test-user-id",
        role="soc_analyst",
    )

    from app.config import get_settings

    settings = get_settings()

    payload = decode_token(
        token,
        settings.jwt_secret,
    )

    assert payload["sub"] == "test-user-id"
    assert payload["role"] == "soc_analyst"
    assert payload["typ"] == "access"
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload


def test_security_headers():
    """
    Verify the important security headers are emitted by FastAPI.
    """
    response = client.get("/api/v1/auth/password-rules")

    assert response.status_code == 200

    headers = response.headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"

    csp = headers["content-security-policy"]

    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "connect-src" in csp


def test_correlation_id_is_returned():
    correlation_id = "test-correlation-id-123"

    response = client.get(
        "/api/v1/auth/password-rules",
        headers={
            "X-Correlation-ID": correlation_id,
        },
    )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == correlation_id


def test_unknown_endpoint_returns_404():
    response = client.get("/api/v1/this-route-does-not-exist")

    assert response.status_code == 404
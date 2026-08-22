import pytest
from app.auth.security import hash_password, verify_password, create_access_token, decode_token

def test_password_hashing():
    raw_pwd = "SuperSecretPassword123!"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_encode_decode():
    payload = {"sub": "user_12345", "email": "test@biomindq.ai"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_12345"
    assert decoded["email"] == "test@biomindq.ai"
    assert decoded["type"] == "access"

@pytest.mark.asyncio
async def test_trial_token_gate():
    from app.auth.dependencies import TRIAL_COOKIE_NAME
    # Verify logic for anonymous vs authenticated
    from fastapi import Request, Response
    pass

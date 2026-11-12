import pytest
from bullsutra.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
)
from bullsutra.core.errors import Unauthorized

def test_password_hashing():
    pw = "supersecretpassword123"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(pw, h)
    assert not verify_password("wrongpassword", h)

def test_jwt_tokens():
    user_id = "0b494477-126a-4293-8882-f9e737aecd4a"
    access_tok = create_access_token(user_id, role="admin")
    refresh_tok = create_refresh_token(user_id, role="admin")

    # Decode access token
    payload = decode_token(access_tok, expected_typ="access")
    assert payload["sub"] == user_id
    assert payload["role"] == "admin"
    assert payload["typ"] == "access"

    # Refresh token cannot be decoded as access
    with pytest.raises(Unauthorized, match="token"):
        decode_token(refresh_tok, expected_typ="access")

    # Refresh token decoded as refresh
    payload_ref = decode_token(refresh_tok, expected_typ="refresh")
    assert payload_ref["sub"] == user_id
    assert payload_ref["typ"] == "refresh"

def test_api_key_generation():
    raw_key, prefix, key_hash = generate_api_key()
    assert raw_key.startswith("bsk_")
    assert prefix == raw_key[:8]
    assert hash_api_key(raw_key) == key_hash

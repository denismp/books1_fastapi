# test/test_auth.py
import pytest
from datetime import timedelta
from jose import jwt
from fastapi import HTTPException

from todo.routers.auth import (
    create_access_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)


def test_create_access_token():
    payload = {
        "sub": "testuser",
        "id": 1,
        "role": "user"
    }
    expires_delta = timedelta(days=1)

    token = create_access_token(payload, expires_delta)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert decoded["sub"] == "testuser"
    assert decoded["id"] == 1
    assert decoded["role"] == "user"
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_get_current_user_missing_payload():
    # Token missing required `sub` and `id`
    payload = {"role": "user"}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=token)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Could not validate credentials"

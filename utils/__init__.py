import os
import uuid

import bcrypt
import jwt
import datetime

from flask import Request

from utils.api import ApiStatus


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(hashed: str, password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

class JWT:
    def __init__(self, secret: str, default_minutes: int = 60):
        self.minutes = max(default_minutes, 1)
        self._secret = secret
    def generate(self, minutes: int | None = None, **kwargs: any) -> str:
        payload = {
            **kwargs,
            "expiration": datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(minutes=self.minutes or minutes))
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
    def get_keys(self, token: str, *keys: str):
        payload = self.get(token)
        for key in keys:
            if key not in payload.keys():
                raise ApiStatus(400, f"Token doesn't contain '{key}' key")

        return [payload.get(key) for key in keys]
    def get(self, token: str) -> dict[str, any]:
        try:
            return jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ApiStatus(401, "Token expired")
        except jwt.InvalidTokenError:
            raise ApiStatus(401, "Invalid token")
    def expires(self, token: str, seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0, weeks: int = 0) -> bool:
        payload = self.get(token)
        expiration = datetime.datetime.fromtimestamp(payload['expiration'], datetime.UTC)
        return (expiration - datetime.datetime.now(datetime.UTC)) < datetime.timedelta(seconds=seconds, minutes=minutes,
                                                                                       hours=hours, days=days,
                                                                                       weeks=weeks)

def get_env(*keys: str, default: any = None) -> dict[str, str] | list[str] | str | None:
    if len(keys) == 0:
        return dict(os.environ) or default
    if len(keys) == 1:
        return os.getenv(keys[0], default)
    else:
        return [os.getenv(key, default) for key in keys]
def get_user_id(request: Request, jwt: JWT, token: str | None = None) -> uuid.UUID:
    # Gets token from 'Authentication' header
    t = token or request.headers.get('Authentication')
    if t is None:
        raise ApiStatus(401, "'Authentication' header not present")
    payload = jwt.get(t)
    return payload.get('user_id')

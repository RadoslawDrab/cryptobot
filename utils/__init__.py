import uuid

import bcrypt
import jwt
import datetime

from utils.api import ApiStatus

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(hashed: str, password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


SECRET_KEY = "your-secret-key"  # Keep this secret and secure!


def generate_jwt(user_id: uuid.UUID, minutes: int = 60) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_jwt(token: str) -> tuple[uuid.UUID, datetime.datetime]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"], datetime.datetime.fromtimestamp(payload['exp'], datetime.UTC)
    except jwt.ExpiredSignatureError:
        raise ApiStatus(401, "Token expired")
    except jwt.InvalidTokenError:
        raise ApiStatus(401, "Invalid token")

def jwt_expires(token: str, seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0, weeks: int = 0) -> bool:
    _, expiration = verify_jwt(token)
    return (expiration - datetime.datetime.now(datetime.UTC)) < datetime.timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days, weeks=weeks)

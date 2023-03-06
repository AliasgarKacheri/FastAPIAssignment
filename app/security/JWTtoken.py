from datetime import datetime, timedelta
from jose import JWTError, jwt

from app import schemas

SECRET_KEY = "09d25e094faa6ca2556c89563b93f7099f6f0f4caa6cf63b8"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        is_active = payload.get("is_active")
        id = payload.get("id")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email, role=role, is_active=is_active, id=id)
        return token_data
    except JWTError:
        raise credentials_exception

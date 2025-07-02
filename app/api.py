import io
from datetime import datetime, timedelta, timezone
from typing import Any

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response
import matplotlib.pyplot as plt
from jose import jwt

from app.db import offset_metric, avg_pull_request_interval
from app.settings import Settings


settings = Settings()  # type: ignore
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake user just for assignment
fake_users_db = {
    "datamoleuser": {"username": "datamoleuser", "password": "datamolepass"}
}
SECRET_KEY = settings.SECRET_KEY
DB_PATH = settings.DB_PATH
ALGORITHM = settings.ALGORITHM


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    user = fake_users_db.get(username)
    if not user or user["password"] != password:
        return None
    return user


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/health", tags=["infra"])
def health(response: Response) -> dict[str, str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "nok", "detail": str(e)}


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/offset_metrics")
def get_offset_metrics(offset: int, _: str = Depends(verify_token)):
    result = offset_metric(offset)

    return {"metrics": result}


@router.get("/avg_pull_metrics")
def get_avg_pull_request_interval(_: str = Depends(verify_token)):
    result = avg_pull_request_interval()

    return {"metrics": result}


@router.get("/event_type_chart")
def event_type_chart(_: str = Depends(verify_token)):
    # Sample: get counts from DB
    data = {"PullRequestEvent": 10, "IssuesEvent": 5, "WatchEvent": 3}
    fig, ax = plt.subplots()
    ax.bar(data.keys(), data.values())
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Response(buf.read(), media_type="image/png")

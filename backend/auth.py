# backend/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
import os, sqlite3
from .task_manager import DB_PATH, init_db

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_env")
ALGORITHM = "HS256"
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class Credentials(BaseModel):
    email: EmailStr
    password: str

def _get_conn():
    return sqlite3.connect(DB_PATH)

def _ensure_users_table():
    with _get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL
        );
        """)
        conn.commit()

@router.post("/register")
def register(creds: Credentials):
    _ensure_users_table()
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE email=?", (creds.email,))
        if cur.fetchone():
            raise HTTPException(400, "User already exists")
        cur.execute(
            "INSERT INTO users(email, password_hash) VALUES(?,?)",
            (creds.email, pwd_ctx.hash(creds.password)),
        )
        conn.commit()
    return {"message": "Registered successfully."}

@router.post("/login")
def login(creds: Credentials):
    _ensure_users_table()
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE email=?", (creds.email,))
        row = cur.fetchone()
        if not row or not pwd_ctx.verify(creds.password, row[0]):
            raise HTTPException(401, "Invalid email or password")
    token = jwt.encode({"sub": creds.email}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

def get_current_user_email(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(401, "Invalid token")
        return email
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

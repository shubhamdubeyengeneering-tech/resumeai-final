import os, sqlite3
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), 'resumeai.db')
SECRET_KEY = os.getenv('AUTH_SECRET_KEY', 'resumeai-development-secret-change-later')
ALGORITHM = 'HS256'
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
password_hash = PasswordHash.recommended()
auth_router = APIRouter(prefix='/auth', tags=['Authentication'])

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    conn.commit(); conn.close()
init_db()

class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=6, max_length=128)
class LoginRequest(BaseModel):
    email: str
    password: str

def create_access_token(user_id: int, email: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({'sub': str(user_id), 'email': email, 'exp': expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Authentication required.')
    token = authorization.split(' ', 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload['sub'])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired login session.')
    conn = get_db()
    user = conn.execute('SELECT id, name, email, created_at FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail='User account not found.')
    return dict(user)

@auth_router.post('/signup')
def signup(data: SignupRequest):
    name, email = data.name.strip(), data.email.strip().lower()
    if not name: raise HTTPException(status_code=400, detail='Name is required.')
    if '@' not in email: raise HTTPException(status_code=400, detail='Please enter a valid email address.')
    conn = get_db()
    if conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
        conn.close(); raise HTTPException(status_code=409, detail='An account with this email already exists.')
    cur = conn.execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',
                       (name, email, password_hash.hash(data.password), datetime.now(timezone.utc).isoformat()))
    user_id = cur.lastrowid; conn.commit(); conn.close()
    token = create_access_token(user_id, email)
    return {'success': True, 'message': 'Account created successfully.', 'access_token': token, 'token_type': 'bearer',
            'user': {'id': user_id, 'name': name, 'email': email}}

@auth_router.post('/login')
def login(data: LoginRequest):
    email = data.email.strip().lower(); conn = get_db()
    user = conn.execute('SELECT id,name,email,password_hash,created_at FROM users WHERE email=?', (email,)).fetchone(); conn.close()
    if not user or not password_hash.verify(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Incorrect email or password.')
    token = create_access_token(user['id'], user['email'])
    return {'success': True, 'message': 'Login successful.', 'access_token': token, 'token_type': 'bearer',
            'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}}

@auth_router.get('/health')
def auth_health(): return {'success': True, 'message': 'Authentication system is working.'}

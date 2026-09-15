import os, sqlite3, urllib.parse, re, hashlib, uuid, smtplib, ssl, threading, secrets
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

try:
    from authlib.integrations.starlette_client import OAuth
except Exception:
    OAuth = None


DB_PATH = os.getenv('RESUMEAI_DB_PATH', os.path.join(os.path.dirname(__file__), 'resumeai.db'))
SECRET_KEY = os.getenv('AUTH_SECRET_KEY', 'resumeai-development-secret-change-later')
ALGORITHM = 'HS256'
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
password_hash = PasswordHash.recommended()
FRONTEND_URL = os.getenv('RESUMEAI_FRONTEND_URL', 'http://localhost:5173').rstrip('/')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', '').strip() or 'http://localhost:8000/auth/google/callback'

oauth = OAuth() if OAuth else None
if oauth and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


def _send_security_login_email(to_email: str, name: str, method: str = 'Email and password'):
    host = os.getenv('RESUMEAI_SMTP_HOST', 'smtp.gmail.com').strip()
    try: port = int(os.getenv('RESUMEAI_SMTP_PORT', '465'))
    except Exception: port = 465
    username = os.getenv('RESUMEAI_SMTP_USER', '').strip()
    password = os.getenv('RESUMEAI_SMTP_PASSWORD', '').strip()
    sender = os.getenv('RESUMEAI_SMTP_FROM', username).strip()
    if not to_email or not username or not password or not sender:
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = 'ResumeAI security alert — new sign-in'
        msg['From'] = sender
        msg['To'] = to_email
        msg.set_content(
            f"Hi {name},\n\nA new sign-in to your ResumeAI account was completed.\n\nSign-in method: {method}\nTime (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\nIf this was not you, change your ResumeAI password and review your account security settings.\n\n— ResumeAI"
        )
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=12) as server:
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        print('ResumeAI login security email error:', repr(exc))
        return False


def _send_welcome_email(to_email: str, name: str):
    host = os.getenv('RESUMEAI_SMTP_HOST', 'smtp.gmail.com').strip()
    try: port = int(os.getenv('RESUMEAI_SMTP_PORT', '465'))
    except Exception: port = 465
    username = os.getenv('RESUMEAI_SMTP_USER', '').strip()
    password = os.getenv('RESUMEAI_SMTP_PASSWORD', '').strip()
    sender = os.getenv('RESUMEAI_SMTP_FROM', username).strip()
    if not to_email or not username or not password or not sender:
        return
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Welcome to ResumeAI 🤖'
        msg['From'] = sender
        msg['To'] = to_email
        msg.set_content(f"Hi {name},\n\nYour ResumeAI account is ready. Your resume analyses, applications, interview practice and workspace settings are tied to this account.\n\n— ResumeAI")
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=12) as server:
            server.login(username, password)
            server.send_message(msg)
    except Exception as exc:
        print('ResumeAI welcome email error:', repr(exc))


auth_router = APIRouter(prefix='/auth', tags=['Authentication'])

def get_db():
    # Render can receive several requests at the same time. SQLite allows only
    # one writer, so wait for an active writer instead of failing immediately.
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # Another process may be changing the journal mode at startup. The
        # busy_timeout above is still enough to wait for the lock.
        pass
    conn.execute("PRAGMA synchronous=NORMAL")
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

def get_current_user(
    authorization: str | None = Header(default=None),
    x_guest_id: str | None = Header(default=None),
):
    # Logged-in accounts continue to work exactly as before.
    if authorization and authorization.lower().startswith('bearer '):
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

    # Guest mode: the website can be used without forcing signup/login.
    # A stable browser-generated guest id keeps that visitor's workspace data
    # separate without exposing or requiring an account password.
    guest_id = (x_guest_id or '').strip()
    if guest_id:
        guest_id = re.sub(r'[^A-Za-z0-9_-]', '', guest_id)[:80]
        if guest_id:
            guest_email = 'guest-' + hashlib.sha256(guest_id.encode()).hexdigest()[:32] + '@guest.resumeai.local'
            conn = get_db()
            row = conn.execute('SELECT id, name, email, created_at FROM users WHERE email=?', (guest_email,)).fetchone()
            if not row:
                # INSERT OR IGNORE also protects against two simultaneous
                # guest requests creating the same guest record.
                conn.execute(
                    'INSERT OR IGNORE INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',
                    ('Guest User', guest_email, password_hash.hash(uuid.uuid4().hex), datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
                row = conn.execute('SELECT id, name, email, created_at FROM users WHERE email=?', (guest_email,)).fetchone()
            conn.close()
            user = dict(row)
            user['email'] = ''
            user['is_guest'] = True
            return user

    raise HTTPException(status_code=401, detail='Authentication required.')

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
    threading.Thread(target=_send_welcome_email, args=(email, name), daemon=True).start()
    return {'success': True, 'message': 'Account created successfully.', 'access_token': token, 'token_type': 'bearer',
            'user': {'id': user_id, 'name': name, 'email': email}}

@auth_router.post('/login')
def login(data: LoginRequest):
    email = data.email.strip().lower(); conn = get_db()
    user = conn.execute('SELECT id,name,email,password_hash,created_at FROM users WHERE email=?', (email,)).fetchone(); conn.close()
    if not user or not password_hash.verify(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Incorrect email or password.')
    token = create_access_token(user['id'], user['email'])
    threading.Thread(target=_send_security_login_email, args=(user['email'], user['name'], 'Email and password'), daemon=True).start()
    return {'success': True, 'message': 'Login successful.', 'access_token': token, 'token_type': 'bearer',
            'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}}

@auth_router.get('/google/start')
async def google_start(request: __import__('fastapi').Request):
    if not oauth or not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(503, 'Google login is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to the backend environment.')
    redirect_uri = GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get('/google/callback')
async def google_callback(request: __import__('fastapi').Request):
    if not oauth:
        raise HTTPException(503, 'Google login is not configured.')
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get('userinfo')
        if not userinfo:
            userinfo = await oauth.google.userinfo(token=token)
        email = str(userinfo.get('email') or '').strip().lower()
        name = str(userinfo.get('name') or userinfo.get('given_name') or 'Google User').strip()
        if not email:
            raise HTTPException(400, 'Google did not return an email address.')
        conn=get_db(); row=conn.execute('SELECT id,name,email FROM users WHERE email=?',(email,)).fetchone()
        if not row:
            cur=conn.execute('INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)',(name,email,password_hash.hash(secrets.token_urlsafe(24)),datetime.now(timezone.utc).isoformat()))
            user_id=cur.lastrowid; conn.commit()
        else:
            user_id=row['id']
            conn.execute('UPDATE users SET name=? WHERE id=?',(name,user_id)); conn.commit()
        conn.close()
        access_token=create_access_token(user_id,email)
        threading.Thread(target=_send_security_login_email, args=(email, name, 'Google'), daemon=True).start()
        from starlette.responses import RedirectResponse
        return RedirectResponse(f"{FRONTEND_URL}/?google_token={urllib.parse.quote(access_token)}")
    except HTTPException:
        raise
    except Exception as exc:
        print('Google OAuth error:', repr(exc))
        from starlette.responses import RedirectResponse
        return RedirectResponse(f"{FRONTEND_URL}/?google_error=Google%20login%20could%20not%20be%20completed")


@auth_router.get('/health')
def auth_health(): return {'success': True, 'message': 'Authentication system is working.'}

@auth_router.get('/me')
def auth_me(user=__import__('fastapi').Depends(get_current_user)):
    return {'success': True, 'user': user}

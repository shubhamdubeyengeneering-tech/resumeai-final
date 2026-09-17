import json, os, sqlite3, urllib.parse, urllib.request, smtplib, ssl, re, threading, time
from email.message import EmailMessage
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user, get_db

features_router = APIRouter(prefix='/api', tags=['ResumeAI Workspace'])


def _send_email(to_email: str, subject: str, body: str):
    """Send optional real email notifications when SMTP is configured.
    Credentials are read only from environment variables; never hard-code them.
    Gmail users can use smtp.gmail.com with a Gmail App Password.
    """
    host = os.getenv('RESUMEAI_SMTP_HOST', 'smtp.gmail.com').strip()
    port = int(os.getenv('RESUMEAI_SMTP_PORT', '465'))
    username = os.getenv('RESUMEAI_SMTP_USER', '').strip()
    password = os.getenv('RESUMEAI_SMTP_PASSWORD', '').strip()
    sender = os.getenv('RESUMEAI_SMTP_FROM', username).strip()
    if not to_email or not username or not password or not sender:
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to_email
        msg.set_content(body)
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=12) as server:
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        print('ResumeAI email notification error:', repr(exc))
        return False


def _email_notifications_enabled(user_id: int) -> bool:
    conn = db()
    row = conn.execute('SELECT email_notifications FROM settings WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return bool(row['email_notifications']) if row else True


def _notify_user(user_id: int, subject: str, body: str):
    _add_notification(user_id, subject, body, 'career')
    if not _email_notifications_enabled(user_id):
        return
    conn = db()
    row = conn.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if row and row['email'] and '@' in row['email']:
        _send_email(row['email'], subject, body)


def init_feature_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY, phone TEXT DEFAULT '', location TEXT DEFAULT '', headline TEXT DEFAULT '', bio TEXT DEFAULT '', skills TEXT DEFAULT '', photo TEXT DEFAULT '', updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, email_notifications INTEGER DEFAULT 1, weekly_summary INTEGER DEFAULT 1, language TEXT DEFAULT 'English', theme TEXT DEFAULT 'system', voice_enabled INTEGER DEFAULT 1, voice_gender TEXT DEFAULT 'female', updated_at TEXT NOT NULL, lock_enabled INTEGER DEFAULT 0, lock_pin_hash TEXT DEFAULT '')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS notification_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, kind TEXT DEFAULT 'career', read INTEGER DEFAULT 0, created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS notification_digest_log (user_id INTEGER PRIMARY KEY, last_sent_at TEXT DEFAULT '')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, company TEXT NOT NULL, role TEXT NOT NULL, location TEXT DEFAULT '', url TEXT DEFAULT '', status TEXT DEFAULT 'Applied', notes TEXT DEFAULT '', applied_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, role TEXT NOT NULL, question TEXT NOT NULL, answer TEXT DEFAULT '', score INTEGER, feedback TEXT DEFAULT '', created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_interview_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, role TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'English', resume_job_id TEXT DEFAULT '', total_questions INTEGER NOT NULL DEFAULT 10, current_question INTEGER NOT NULL DEFAULT 1, completed INTEGER NOT NULL DEFAULT 0, final_score REAL, final_feedback TEXT DEFAULT '', created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_interview_turns (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, question_number INTEGER NOT NULL, question TEXT NOT NULL, answer TEXT DEFAULT '', score INTEGER, feedback TEXT DEFAULT '', strengths TEXT DEFAULT '', improvement TEXT DEFAULT '', created_at TEXT NOT NULL)''')
    # Safe migration for settings created by older ResumeAI versions.
    cols = {r[1] for r in conn.execute('PRAGMA table_info(settings)').fetchall()}
    if 'theme' not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN theme TEXT DEFAULT 'system'")
    if 'voice_enabled' not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN voice_enabled INTEGER DEFAULT 1")
    if 'voice_gender' not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN voice_gender TEXT DEFAULT 'female'")
    profile_cols = {r[1] for r in conn.execute('PRAGMA table_info(profiles)').fetchall()}
    if 'photo' not in profile_cols:
        conn.execute("ALTER TABLE profiles ADD COLUMN photo TEXT DEFAULT ''")
    if 'lock_enabled' not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN lock_enabled INTEGER DEFAULT 0")
    if 'lock_pin_hash' not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN lock_pin_hash TEXT DEFAULT ''")
    mock_cols = {r[1] for r in conn.execute('PRAGMA table_info(mock_interview_sessions)').fetchall()}
    if 'cancelled' not in mock_cols:
        conn.execute("ALTER TABLE mock_interview_sessions ADD COLUMN cancelled INTEGER DEFAULT 0")
    if 'target_goal' not in mock_cols:
        conn.execute("ALTER TABLE mock_interview_sessions ADD COLUMN target_goal TEXT DEFAULT ''")
    conn.commit(); conn.close()


init_feature_db()


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    return get_db()


def _hash_lock_pin(pin: str) -> str:
    from pwdlib import PasswordHash
    return PasswordHash.recommended().hash(pin) if pin else ''

def _verify_lock_pin(pin: str, hashed: str) -> bool:
    if not pin or not hashed:
        return False
    try:
        from pwdlib import PasswordHash
        return PasswordHash.recommended().verify(pin, hashed)
    except Exception:
        return False

def _add_notification(user_id: int, title: str, body: str, kind: str = 'career'):
    try:
        conn = db()
        conn.execute('INSERT INTO notification_events(user_id,title,body,kind,created_at) VALUES(?,?,?,?,?)', (user_id, title, body, kind, now()))
        conn.commit(); conn.close()
    except Exception as exc:
        print('ResumeAI notification event error:', repr(exc))



class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(default='', max_length=30)
    location: str = Field(default='', max_length=120)
    headline: str = Field(default='', max_length=160)
    bio: str = Field(default='', max_length=1000)
    skills: str = Field(default='', max_length=1000)
    photo: str = Field(default='', max_length=3000000)


class SettingsUpdate(BaseModel):
    email_notifications: bool = True
    weekly_summary: bool = True
    language: str = 'English'
    theme: str = 'system'
    voice_enabled: bool = True
    voice_gender: str = 'female'
    lock_enabled: bool | None = None
    lock_pin: str | None = Field(default=None, max_length=12)


class LockVerify(BaseModel):
    pin: str = Field(min_length=4, max_length=12)


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=180)
    location: str = Field(default='', max_length=150)
    url: str = Field(default='', max_length=1000)
    status: str = 'Applied'
    notes: str = Field(default='', max_length=2000)


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    url: str | None = None
    status: str | None = None
    notes: str | None = None


class MockStart(BaseModel):
    role: str = Field(min_length=2, max_length=100)
    target_goal: str = Field(default='', max_length=180)
    language: str = Field(default='English', max_length=20)
    resume_job_id: str = Field(default='', max_length=120)


class MockAnswer(BaseModel):
    answer: str = Field(min_length=2, max_length=4000)


@features_router.get('/me')
def me(user=Depends(get_current_user)):
    return {'success': True, 'user': user}


@features_router.get('/profile')
def get_profile(user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT * FROM profiles WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row:
        return {'success': True, 'profile': {'name': user['name'], 'email': user['email'], 'phone': '', 'location': '', 'headline': '', 'bio': '', 'skills': '', 'photo': ''}}
    d = dict(row); d.pop('user_id', None); d.pop('updated_at', None)
    return {'success': True, 'profile': {'name': user['name'], 'email': user['email'], **d}}


@features_router.put('/profile')
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    conn = db(); ts = now()
    photo = data.photo.strip()
    if photo and not photo.startswith('data:image/'):
        raise HTTPException(400, 'Profile photo must be a valid image data URL.')
    conn.execute('''INSERT INTO profiles(user_id,phone,location,headline,bio,skills,photo,updated_at) VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone,location=excluded.location,headline=excluded.headline,bio=excluded.bio,skills=excluded.skills,photo=excluded.photo,updated_at=excluded.updated_at''',
                 (user['id'], data.phone.strip(), data.location.strip(), data.headline.strip(), data.bio.strip(), data.skills.strip(), photo, ts))
    conn.execute('UPDATE users SET name=? WHERE id=?', (data.name.strip(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'Profile saved.'}


@features_router.get('/settings')
def get_settings(user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT * FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row:
        return {'success': True, 'settings': {'email_notifications': True, 'weekly_summary': True, 'language': 'English', 'theme': 'light', 'voice_enabled': True, 'voice_gender': 'female', 'lock_enabled': False, 'lock_configured': False}}
    d = dict(row)
    return {'success': True, 'settings': {'email_notifications': bool(d['email_notifications']), 'weekly_summary': bool(d['weekly_summary']), 'language': d['language'], 'theme': 'dark' if d.get('theme') == 'dark' else 'light', 'voice_enabled': bool(d.get('voice_enabled', 1)), 'voice_gender': d.get('voice_gender') or 'female', 'lock_enabled': bool(d.get('lock_enabled', 0)), 'lock_configured': bool(d.get('lock_pin_hash'))}}


@features_router.put('/settings')
def update_settings(data: SettingsUpdate, user=Depends(get_current_user)):
    language = data.language if data.language in {'English', 'Hindi'} else 'English'
    theme = 'dark' if data.theme == 'dark' else 'light'
    voice_gender = data.voice_gender if data.voice_gender in {'female', 'male'} else 'female'
    conn = db()
    existing = conn.execute('SELECT * FROM settings WHERE user_id=?', (user['id'],)).fetchone()
    ts = now()
    if existing:
        current = dict(existing)
        lock_enabled = int(current.get('lock_enabled', 0)) if data.lock_enabled is None else int(data.lock_enabled)
        lock_hash = current.get('lock_pin_hash') or ''
        if data.lock_pin is not None and data.lock_pin.strip() and lock_enabled:
            lock_hash = _hash_lock_pin(data.lock_pin.strip())
        if lock_enabled and not lock_hash:
            conn.close()
            raise HTTPException(400, 'Set a PIN in Security before enabling website lock.')
        conn.execute("UPDATE settings SET email_notifications=?,weekly_summary=?,language=?,theme=?,voice_enabled=?,voice_gender=?,updated_at=?,lock_enabled=?,lock_pin_hash=? WHERE user_id=?",
                     (int(data.email_notifications), int(data.weekly_summary), language, theme, int(data.voice_enabled), voice_gender, ts, lock_enabled, lock_hash, user['id']))
    else:
        lock_enabled = int(data.lock_enabled) if data.lock_enabled is not None else 0
        pin = (data.lock_pin or '').strip()
        if lock_enabled and (len(pin) < 4 or not pin.isdigit()):
            conn.close(); raise HTTPException(400, 'Set a PIN in Security before enabling website lock.')
        lock_hash = _hash_lock_pin(pin) if lock_enabled else ''
        conn.execute("INSERT INTO settings(user_id,email_notifications,weekly_summary,language,theme,voice_enabled,voice_gender,updated_at,lock_enabled,lock_pin_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     (user['id'], int(data.email_notifications), int(data.weekly_summary), language, theme, int(data.voice_enabled), voice_gender, ts, lock_enabled, lock_hash))
    conn.commit(); conn.close()
    return {'success': True, 'message': 'Settings saved.'}


class PinSetup(BaseModel):
    pin: str = Field(min_length=4, max_length=12)
    confirm_pin: str = Field(min_length=4, max_length=12)

class PinChange(BaseModel):
    current_pin: str = Field(min_length=4, max_length=12)
    new_pin: str = Field(min_length=4, max_length=12)
    confirm_new_pin: str = Field(min_length=4, max_length=12)

class PinDisable(BaseModel):
    current_pin: str = Field(min_length=4, max_length=12)

@features_router.get('/security/status')
def security_status(user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT lock_enabled,lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    return {'success': True, 'lock_enabled': bool(row['lock_enabled']) if row else False, 'lock_configured': bool(row and row['lock_pin_hash'])}

@features_router.post('/security/set-pin')
def security_set_pin(data: PinSetup, user=Depends(get_current_user)):
    pin = data.pin.strip(); confirm = data.confirm_pin.strip()
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 12:
        raise HTTPException(400, 'PIN must contain 4-12 digits.')
    if pin != confirm:
        raise HTTPException(400, 'PIN and confirmation do not match.')
    conn = db(); ts = now(); hashed = _hash_lock_pin(pin)
    existing = conn.execute('SELECT user_id FROM settings WHERE user_id=?', (user['id'],)).fetchone()
    if existing:
        conn.execute('UPDATE settings SET lock_enabled=0,lock_pin_hash=?,updated_at=? WHERE user_id=?', (hashed, ts, user['id']))
    else:
        conn.execute("INSERT INTO settings(user_id,updated_at,lock_enabled,lock_pin_hash) VALUES(?,?,0,?)", (user['id'], ts, hashed))
    conn.commit(); conn.close()
    return {'success': True, 'message': 'PIN created successfully. Website Lock is currently off.', 'lock_enabled': False, 'lock_configured': True}

@features_router.post('/security/change-pin')
def security_change_pin(data: PinChange, user=Depends(get_current_user)):
    current_pin, new_pin, confirm = data.current_pin.strip(), data.new_pin.strip(), data.confirm_new_pin.strip()
    conn = db(); row = conn.execute('SELECT lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row or not row['lock_pin_hash'] or not _verify_lock_pin(current_pin, row['lock_pin_hash']):
        raise HTTPException(401, 'Current PIN is incorrect.')
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 12:
        raise HTTPException(400, 'New PIN must contain 4-12 digits.')
    if new_pin != confirm:
        raise HTTPException(400, 'New PIN and confirmation do not match.')
    conn = db(); conn.execute('UPDATE settings SET lock_enabled=0,lock_pin_hash=?,updated_at=? WHERE user_id=?', (_hash_lock_pin(new_pin), now(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'PIN changed successfully. Website Lock remains unchanged.', 'lock_enabled': False, 'lock_configured': True}

class PinEnable(BaseModel):
    current_pin: str = Field(min_length=4, max_length=12)

@features_router.post('/security/enable-lock')
def security_enable_lock(data: PinEnable, user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row or not row['lock_pin_hash'] or not _verify_lock_pin(data.current_pin.strip(), row['lock_pin_hash']):
        raise HTTPException(401, 'Current PIN is incorrect.')
    conn = db(); conn.execute('UPDATE settings SET lock_enabled=1,updated_at=? WHERE user_id=?', (now(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'Website lock enabled.', 'lock_enabled': True, 'lock_configured': True}

@features_router.post('/security/disable-lock')
def security_disable_lock(data: PinDisable, user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row or not row['lock_pin_hash'] or not _verify_lock_pin(data.current_pin.strip(), row['lock_pin_hash']):
        raise HTTPException(401, 'Current PIN is incorrect.')
    conn = db(); conn.execute('UPDATE settings SET lock_enabled=0,updated_at=? WHERE user_id=?', (now(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'Website lock disabled.', 'lock_enabled': False, 'lock_configured': True}


@features_router.post('/security/remove-pin')
def security_remove_pin(data: PinDisable, user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row or not row['lock_pin_hash'] or not _verify_lock_pin(data.current_pin.strip(), row['lock_pin_hash']):
        raise HTTPException(401, 'Current PIN is incorrect.')
    conn = db(); conn.execute("UPDATE settings SET lock_enabled=0,lock_pin_hash='',updated_at=? WHERE user_id=?", (now(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'PIN removed successfully. Website Lock is now off.', 'lock_enabled': False, 'lock_configured': False}


@features_router.post('/security/verify-lock')
def verify_lock(data: LockVerify, user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT lock_enabled,lock_pin_hash FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row or not row['lock_enabled']:
        return {'success': True, 'locked': False, 'verified': True}
    ok = _verify_lock_pin(data.pin, row['lock_pin_hash'])
    return {'success': True, 'locked': True, 'verified': ok, 'message': 'PIN accepted.' if ok else 'Incorrect PIN.'}


@features_router.get('/notifications')
def notifications(user=Depends(get_current_user)):
    conn = db(); rows = conn.execute('SELECT id,title,body,kind,read,created_at FROM notification_events WHERE user_id=? ORDER BY id DESC LIMIT 50', (user['id'],)).fetchall(); conn.close()
    return {'success': True, 'notifications': [dict(r) for r in rows], 'unread': sum(1 for r in rows if not r['read'])}


@features_router.post('/notifications/{notification_id}/read')
def mark_notification_read(notification_id: int, user=Depends(get_current_user)):
    conn = db(); conn.execute('UPDATE notification_events SET read=1 WHERE id=? AND user_id=?', (notification_id, user['id'])); conn.commit(); conn.close()
    return {'success': True}


@features_router.post('/notifications/read-all')
def mark_all_notifications_read(user=Depends(get_current_user)):
    conn = db(); conn.execute('UPDATE notification_events SET read=1 WHERE user_id=?', (user['id'],)); conn.commit(); conn.close()
    return {'success': True}


@features_router.get('/applications')
def list_applications(user=Depends(get_current_user)):
    conn = db(); rows = conn.execute('SELECT * FROM applications WHERE user_id=? ORDER BY id DESC', (user['id'],)).fetchall(); conn.close()
    return {'success': True, 'applications': [dict(r) for r in rows]}


@features_router.post('/applications')
def add_application(data: ApplicationCreate, user=Depends(get_current_user)):
    conn = db(); cur = conn.execute('INSERT INTO applications(user_id,company,role,location,url,status,notes,applied_at) VALUES(?,?,?,?,?,?,?,?)',
                                     (user['id'], data.company.strip(), data.role.strip(), data.location.strip(), data.url.strip(), data.status.strip(), data.notes.strip(), now()))
    conn.commit(); row = conn.execute('SELECT * FROM applications WHERE id=?', (cur.lastrowid,)).fetchone(); conn.close()
    _notify_user(user['id'], 'ResumeAI — application added', f"Your application for {data.role.strip()} at {data.company.strip()} was saved to your ResumeAI workspace.\n\nStatus: {data.status.strip()}\nLocation: {data.location.strip() or 'Not specified'}")
    return {'success': True, 'application': dict(row)}


@features_router.patch('/applications/{application_id}')
def edit_application(application_id: int, data: ApplicationUpdate, user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT * FROM applications WHERE id=? AND user_id=?', (application_id, user['id'])).fetchone()
    if not row:
        conn.close(); raise HTTPException(404, 'Application not found.')
    fields = []; vals = []
    for key in ['company', 'role', 'location', 'url', 'status', 'notes']:
        val = getattr(data, key)
        if val is not None:
            fields.append(f'{key}=?'); vals.append(val.strip() if isinstance(val, str) else val)
    if fields:
        vals += [application_id, user['id']]
        conn.execute(f"UPDATE applications SET {','.join(fields)} WHERE id=? AND user_id=?", vals); conn.commit()
    row = conn.execute('SELECT * FROM applications WHERE id=?', (application_id,)).fetchone(); conn.close()
    return {'success': True, 'application': dict(row)}


@features_router.delete('/applications/{application_id}')
def delete_application(application_id: int, user=Depends(get_current_user)):
    conn = db(); cur = conn.execute('DELETE FROM applications WHERE id=? AND user_id=?', (application_id, user['id'])); conn.commit(); conn.close()
    if cur.rowcount == 0: raise HTTPException(404, 'Application not found.')
    return {'success': True}


QUESTION_BANK = {
    'software': [
        'Walk me through one project from your resume. What problem did you solve and what did you personally build?',
        'Suppose a feature works locally but fails in production. How would you investigate it?',
        'Tell me about a technical decision you made and the trade-off you considered.',
        'How do you test a feature before releasing it?',
        'Describe a time you improved performance, reliability, or user experience.',
        'How would you explain a technical concept to a non-technical teammate?',
        'Tell me about a bug or mistake you made and what you learned from it.',
        'How do you decide which task to work on first when several are urgent?',
        'What part of your current skill set would you most like to improve for this role?',
        'Why should a team choose you for this role, based on the experience you can genuinely demonstrate?'
    ],
    'data': [
        'Walk me through an analysis or data project from your resume. What question were you trying to answer?',
        'How would you handle missing, inconsistent, or duplicated data?',
        'Which metric would you choose to measure the success of a feature and why?',
        'How would you explain an unexpected result to a stakeholder?',
        'Tell me about a time your analysis changed a decision or recommendation.',
        'How do you validate that your analysis is not misleading?',
        'What would you do if two data sources disagreed?',
        'How do you communicate uncertainty in your findings?',
        'Which analytical skill would you most like to strengthen for this role?',
        'Why are you a good fit for this role based only on experience you can demonstrate?'
    ],
    'default': [
        'Tell me about yourself and the career direction you are currently pursuing.',
        'Choose one project or experience from your resume and explain your contribution.',
        'Tell me about a challenging problem you faced and how you approached it.',
        'How do you learn a skill that is new to you?',
        'Describe a time you worked with another person or team to complete something important.',
        'What is one achievement you are proud of and what made it meaningful?',
        'Tell me about a mistake or setback and what you learned from it.',
        'How do you prioritize when you have multiple deadlines?',
        'Which skill would make the biggest difference to your career if you improved it?',
        'Why are you a strong candidate for this role based on evidence from your experience?'
    ]
}


QUESTION_BANK_LOCALIZED = {
    'English': QUESTION_BANK,
    'Hindi': {
        'software': [
            'Apne resume ke kisi ek project ko detail mein samjhaiye. Aapne kaunsi problem solve ki aur khud kya banaya?',
            'Agar koi feature local system par chale lekin production mein fail ho, to aap problem kaise investigate karenge?',
            'Kisi technical decision ke baare mein batayiye jo aapne liya aur usmein kaun-sa trade-off socha?',
            'Release se pehle aap kisi feature ko kaise test karenge?',
            'Aisa samay batayiye jab aapne performance, reliability ya user experience improve kiya ho.',
            'Kisi non-technical teammate ko technical concept kaise samjhayenge?',
            'Kisi bug ya galti ke baare mein batayiye aur usse aapne kya seekha.',
            'Jab kai tasks urgent hon, to aap pehle kaunsa task karenge aur kyun?',
            'Is role ke liye aap apni kaunsi skill ko sabse zyada improve karna chahenge?',
            'Aapke genuine experience ke basis par team ko aapko kyun choose karna chahiye?'
        ],
        'data': [
            'Apne resume ke kisi analysis ya data project ko samjhaiye. Aap kis sawal ka jawab dhoondh rahe the?',
            'Missing, inconsistent ya duplicate data ko aap kaise handle karenge?',
            'Kisi feature ki success measure karne ke liye aap kaunsa metric choose karenge aur kyun?',
            'Unexpected result ko stakeholder ko aap kaise samjhayenge?',
            'Aisa samay batayiye jab aapke analysis ne kisi decision ya recommendation ko badla ho.',
            'Aap kaise validate karenge ki aapka analysis misleading nahi hai?',
            'Agar do data sources alag results dein to aap kya karenge?',
            'Apne findings mein uncertainty ko aap kaise communicate karenge?',
            'Is role ke liye aap kaunsi analytical skill sabse zyada strengthen karna chahenge?',
            'Sirf apne demonstrated experience ke basis par aap is role ke liye achhe fit kyun hain?'
        ],
        'default': [
            'Apne baare mein batayiye aur aap kis career direction mein jana chahte hain?',
            'Apne resume ke kisi project ya experience ko choose karke apna contribution samjhaiye.',
            'Kisi challenging problem ke baare mein batayiye aur aapne use kaise solve kiya.',
            'Aap koi nayi skill kaise seekhte hain?',
            'Team ya kisi doosre person ke saath kaam karne ka koi important example batayiye.',
            'Kis achievement par aapko sabse zyada garv hai aur kyun?',
            'Kisi mistake ya setback ke baare mein batayiye aur aapne kya seekha.',
            'Multiple deadlines hone par aap priorities kaise decide karte hain?',
            'Kaunsi skill improve karne se aapke career par sabse bada positive impact padega?',
            'Apne real experience ke evidence ke basis par aap strong candidate kyun hain?'
        ]
    }
}


def question_bank_for(role: str, language: str = 'English'):
    r = role.lower()
    if any(x in r for x in ['software', 'developer', 'frontend', 'backend', 'full stack', 'engineer', 'web']):
        key = 'software'
    elif any(x in r for x in ['data', 'analyst', 'analytics']):
        key = 'data'
    else:
        key = 'default'
    if language not in {'English', 'Hindi'}:
        language = 'English'
    bank = QUESTION_BANK_LOCALIZED.get(language, QUESTION_BANK_LOCALIZED['English'])
    return bank[key]


def _mock_ai(prompt: str):
    try:
        from google import genai
        from google.genai import types
        key = os.getenv('GEMINI_API_KEY', '').strip()
        if not key:
            return None
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.getenv('RESUMEAI_MOCK_MODEL', 'gemini-3.7-flash'),
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.35, response_mime_type='application/json', thinking_config=types.ThinkingConfig(thinking_level='low'))
        )
        raw = (response.text or '').strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            raw = raw.replace('json\n', '', 1).strip()
        return json.loads(raw)
    except Exception as exc:
        print('Mock AI error:', repr(exc))
        return None


def _resume_context(resume_job_id: str, user_id: int | None = None):
    if not resume_job_id:
        return ''
    try:
        from main import ai_jobs
        job = ai_jobs.get(resume_job_id) or {}
        text = (job.get('resume_text') or '').strip()
        if text:
            return text[:30000]
    except Exception:
        pass
    try:
        conn = db()
        if user_id is not None:
            row = conn.execute(
                'SELECT resume_text FROM resume_analyses WHERE job_id=? AND user_id=? ORDER BY id DESC LIMIT 1',
                (resume_job_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT resume_text FROM resume_analyses WHERE job_id=? ORDER BY id DESC LIMIT 1',
                (resume_job_id,),
            ).fetchone()
        conn.close()
        return ((row['resume_text'] if row else '') or '')[:30000]
    except Exception:
        return ''


def _resume_profile_for_jobs(resume_text: str):
    text = (resume_text or '').lower()
    skill_catalog = [
        'python','java','javascript','typescript','react','next.js','node.js','fastapi','django','flask',
        'sql','mysql','postgresql','mongodb','excel','power bi','tableau','pandas','numpy','scikit-learn',
        'machine learning','deep learning','tensorflow','pytorch','html','css','tailwind','aws','azure',
        'docker','kubernetes','git','github','figma','ui/ux','figma','c++','c#','php','android','kotlin',
        'spring boot','rest api','data analysis','data science','communication','leadership'
    ]
    skills = [x for x in skill_catalog if x in text]
    role_patterns = [
        ('Software Engineer', ['software engineer','software developer','developer','programmer']),
        ('Frontend Developer', ['frontend','front-end','react developer','ui developer']),
        ('Backend Developer', ['backend','back-end','api developer','fastapi','django','node.js']),
        ('Full Stack Developer', ['full stack','full-stack']),
        ('Data Analyst', ['data analyst','data analysis','power bi','tableau']),
        ('Data Scientist', ['data scientist','machine learning','scikit-learn','tensorflow','pytorch']),
        ('Web Developer', ['web developer','web development','html','css','javascript']),
        ('UI/UX Designer', ['ui/ux','ui ux','figma','user experience','user interface']),
        ('Android Developer', ['android developer','android','kotlin']),
    ]
    roles=[]
    for role, terms in role_patterns:
        if any(term in text for term in terms) and role not in roles:
            roles.append(role)
    if not roles:
        roles=['Software Engineer']
    return {'roles': roles[:6], 'skills': skills[:25]}


def _job_match(job: dict, profile: dict, search: str = '') -> int:
    hay = ' '.join(str(job.get(k) or '') for k in ['title','company','location','description','category','job_type']).lower()
    role_text = ' '.join(profile.get('roles', [])).lower()
    skills = profile.get('skills', [])
    score = 0
    for role in profile.get('roles', []):
        role_words = [w for w in re.findall(r'[a-z0-9]+', role.lower()) if len(w) > 2]
        if role_words and sum(w in hay for w in role_words) >= max(1, len(role_words)//2):
            score += 35
            break
    skill_hits = sum(1 for skill in skills if skill.lower() in hay)
    score += min(45, skill_hits * 9)
    if search:
        search_words = [w for w in re.findall(r'[a-z0-9]+', search.lower()) if len(w)>2]
        if search_words and all(w in hay for w in search_words): score += 20
        elif any(w in hay for w in search_words): score += 8
    return max(0, min(100, score))


def _answer_quality(answer: str, question: str = ''):
    text = re.sub(r'\s+', ' ', (answer or '').strip())
    # Support English and Hindi instead of silently
    # treating non-Latin answers as empty/meaningless.
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’][A-Za-zÀ-ÖØ-öø-ÿ]+)?|[\u0900-\u097F]+", text.lower())
    if not words:
        return 0, 'The answer is empty or contains no readable words.', 0

    compact = re.sub(r'[^\w\u0900-\u097F]+', '', text.lower(), flags=re.UNICODE)
    unique_ratio = len(set(words)) / max(1, len(words))
    alpha_ratio = sum(ch.isalpha() for ch in text) / max(1, len(text))
    repeated = bool(re.search(r'(.)\1{4,}', compact))
    filler = {'asdf', 'qwerty', 'test', 'hello', 'hi', 'abc', 'xyz', 'bahifi', 'blah', 'none', 'nothing', 'ok', 'okay'}

    if len(words) <= 2:
        return 8, 'The answer is too short to evaluate meaningfully.', 0
    if compact in filler or (len(words) <= 4 and unique_ratio < 0.65):
        return 6, 'The answer does not provide enough meaningful content.', 0
    if repeated or alpha_ratio < 0.45 or (any(ch.isdigit() for ch in text) and len(words) <= 2):
        return 5, 'The answer appears to contain mostly noise rather than an interview response.', 0
    if len(words) < 6:
        return 25, 'The answer has some content, but it needs more explanation or a concrete example.', 35

    # Lexical relevance is a safety net for when the AI evaluator is unavailable.
    # Keep common conversational/question words out so generic interview prompts
    # such as "tell me about yourself" are not unfairly penalized.
    q_tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+|[\u0900-\u097F]+", (question or '').lower())
    stop = {
        'what','when','where','which','would','could','should','have','your','this','that','about','from','with','tell','walk','describe','explain',
        'how','why','can','you','are','the','and','for','was','were','did','does','do','is','in','of','to','a','an','me','my','please','give','share',
        'kya','kab','kahan','kaise','kyun','aap','apna','apne','apni','batao','bataye','bataiye','hai','hain','aur','ke','ki','ka','ko','mein','se','par','ek','mujhe','tum','tumhara','aapka'
    }
    q_words = {w for w in q_tokens if len(w) >= 3 and w not in stop}
    a_words = set(words)
    overlap = len(q_words & a_words)
    relevance = 0.55 if not q_words else min(1.0, overlap / max(1, min(4, len(q_words))))

    # Generic prompts need content, not literal keyword overlap.
    generic = bool(re.search(r'\b(tell me about yourself|introduce yourself|yourself|strengths?|weaknesses?|career goals?|why should we hire you|why do you want|अपने बारे|अपना परिचय|आपके बारे|ताकत|कमजोरी|करियर लक्ष्य)\b', question or '', re.I))
    if generic and len(words) >= 10:
        relevance = max(relevance, 0.65)

    score = 40
    score += min(22, len(words) * 0.75)
    score += int(unique_ratio * 10)
    score += int(alpha_ratio * 5)
    if relevance >= 0.5:
        score += 14
    elif relevance < 0.25:
        score -= 28
    elif relevance < 0.5:
        score -= 10
    if any(k in a_words for k in ['example','because','result','impact','built','implemented','solved','learned','improved','measured','achieved','उदाहरण','क्योंकि','नतीजा','सीखा','सुधारा']):
        score += 8

    return max(12, min(92, int(score))), '', int(relevance * 100)

def _fallback_evaluation(answer: str, question_number: int, question: str = ''):
    score, gate_message, relevance = _answer_quality(answer, question)
    if score <= 10:
        return {'score': score, 'feedback': gate_message, 'strengths': 'The response was submitted, but it did not contain enough meaningful interview content.', 'improvement': 'Answer the question directly using your own words and include a real example when possible.'}
    if score <= 30:
        return {'score': score, 'feedback': gate_message or 'The response needs more relevant detail.', 'strengths': 'You attempted the question.', 'improvement': 'Explain what you did, why you did it, and what the result was.'}
    feedback = 'Add a concrete example, your specific action, and the real result if you can support it.' if score < 72 else 'Good structure. Keep the answer specific, evidence-based, and concise.'
    if relevance < 25:
        score = min(score, 30)
        feedback = 'The response does not appear to answer the question. Stay focused on what was asked.'
        improvement = 'Answer the exact question first, then add one relevant example or result.'
    elif relevance < 50:
        score = min(score, 48)
        feedback = 'The answer has some content, but the connection to the question is weak.'
        improvement = 'Directly address the key part of the question before adding extra details.'
    return {'score': score, 'feedback': feedback, 'strengths': 'The response contains meaningful content.', 'improvement': improvement}


def _resume_topic_question(role: str, goal: str, language: str, resume_text: str, used: set[str] | None = None):
    """Build a concrete first question from evidence actually present in the resume."""
    used = used or set()
    text = (resume_text or '').strip()
    lower = text.lower()
    # Prefer project/experience evidence over generic questions. Keep extracted snippets short.
    project_lines = []
    in_project = False
    for raw in text.splitlines():
        line = re.sub(r'^[•●▪◦‣*-]+\s*', '', raw).strip()
        norm = line.lower().rstrip(':')
        if norm in {'projects','project','personal projects','academic projects'}:
            in_project = True; continue
        if in_project and norm in {'experience','work experience','education','skills','certifications','achievements','internship','internships'}:
            in_project = False
        if in_project and line and len(line) >= 4:
            project_lines.append(line)
        if len(project_lines) >= 3:
            break
    skills = []
    m = re.search(r'(?:skills|technical skills)\s*[:\-]?\s*(.+)', text, re.I)
    if m:
        skills = [x.strip() for x in re.split(r'[,|•;]', m.group(1)) if x.strip()][:5]
    goal_text = (goal or role).strip() or role.strip()
    candidates=[]
    if project_lines:
        topic = project_lines[0][:120]
        if language == 'Hindi':
            candidates += [f'आपके रिज्यूमे में "{topic}" का उल्लेख है। इस प्रोजेक्ट में आपने व्यक्तिगत रूप से क्या बनाया और सबसे बड़ी चुनौती क्या थी?',
                           f'आपके "{topic}" प्रोजेक्ट का इस लक्ष्य ({goal_text}) से क्या संबंध है, और इसमें आपकी सबसे महत्वपूर्ण भूमिका क्या थी?']
        else:
            candidates += [f'Your resume lists "{topic}". What did you personally build in this project, and what was the biggest challenge you solved?',
                           f'How does your "{topic}" project support your target goal ({goal_text}), and what was your most important contribution?']
    if skills:
        skill = skills[0][:60]
        if language == 'Hindi':
            candidates.append(f'आपके रिज्यूमे में {skill} कौशल दिखता है। आपने इसे वास्तविक काम या प्रोजेक्ट में कहाँ इस्तेमाल किया है?')
        else:
            candidates.append(f'Your resume mentions {skill}. Where have you actually used this skill in a project, internship or work?')
    return next((q for q in candidates if q.lower() not in used and _mock_language_ok(q, language)), '')


def _goal_specific_fallback(role: str, goal: str, language: str, resume_text: str, used: set[str] | None = None):
    goal_text = (goal or role).strip()
    r = role.lower()
    g = goal_text.lower()
    used = used or set()
    resume_q = _resume_topic_question(role, goal, language, resume_text, used)
    if resume_q:
        return resume_q
    if any(x in r for x in ['developer','engineer','software','frontend','backend','full stack','web']):
        if any(x in g for x in ['project','portfolio','build']):
            candidates = [
                'Which project from your resume best proves you can succeed in this target role, and what did you personally build?',
                'Choose the strongest project on your resume for this goal. What technical decision had the biggest impact?'
            ]
        elif any(x in g for x in ['job','interview','crack','placement']):
            candidates = [
                'For this target role, which skill on your resume are you most confident using in a real job, and where have you demonstrated it?',
                'What part of your resume would you defend most strongly in a technical interview for this role, and why?'
            ]
        else:
            candidates = [
                f'For the target goal "{goal_text}", which skill from your resume should we test first, and how have you used it?',
                'Tell me about a real technical problem from your resume that required you to make a difficult decision.'
            ]
    elif any(x in r for x in ['data','analyst','scientist','analytics']):
        candidates = [
            f'For the target goal "{goal_text}", which data skill on your resume gives you the strongest advantage, and how have you demonstrated it?',
            'Choose a data project from your resume and explain the most important insight or result you produced.'
        ]
    else:
        candidates = [
            f'For the target goal "{goal_text}", which experience on your resume is most relevant, and what did you personally contribute?',
            'Which part of your resume best demonstrates your readiness for this target role, and what evidence supports it?'
        ]
    for q in candidates:
        if q.lower() not in used:
            return q
    return candidates[0]


def _mock_language_ok(text: str, language: str) -> bool:
    value = (text or '').strip()
    if not value:
        return False
    if language == 'Hindi':
        devanagari = len(re.findall(r'[\u0900-\u097F]', value))
        letters = len(re.findall(r'[A-Za-z\u0900-\u097F]', value))
        return devanagari >= 5 and devanagari / max(1, letters) >= 0.30
    return not bool(re.search(r'[\u0900-\u097F]', value))

def _localized_mock_fallback(language: str, kind: str):
    data = {
        'Hindi': {
            'feedback': 'उत्तर को अधिक स्पष्ट, प्रासंगिक और उदाहरण आधारित बनाएं।',
            'strengths': 'आपने प्रश्न का उत्तर देने का प्रयास किया।',
            'improvement': 'अपने वास्तविक अनुभव, आपने क्या किया और उसका परिणाम स्पष्ट रूप से बताएं।',
            'final': 'इंटरव्यू पूरा हुआ। प्रत्येक उत्तर की प्रतिक्रिया देखें और कमजोर क्षेत्रों पर अभ्यास करें.'
        },
        'English': {
            'feedback': 'Make the answer more specific, relevant and evidence-based.',
            'strengths': 'You made a genuine attempt to answer the question.',
            'improvement': 'Explain your real experience, what you did, and the result when you can support it.',
            'final': 'Interview complete. Review each answer and practice the areas that need improvement.'
        }
    }
    return data.get(language, data['English']).get(kind, data['English']['feedback'])


@features_router.post('/mocks/start')
def start_mock(data: MockStart, user=Depends(get_current_user)):
    language = data.language if data.language in {'English', 'Hindi'} else 'English'
    questions = question_bank_for(data.role, language)
    resume_text = _resume_context(data.resume_job_id, user['id'])
    # First question is intentionally local and immediate. The interview must not
    # wait on a Gemini request, especially when no resume is uploaded.
    prior_questions = set()
    question = _resume_topic_question(data.role, data.target_goal, language, resume_text, prior_questions)
    if not question:
        question = _goal_specific_fallback(data.role, data.target_goal, language, resume_text, prior_questions)
    if not question or not _mock_language_ok(question, language):
        unused = questions
        question = unused[int(time.time()) % len(unused)]
    conn = db()
    prior = conn.execute('SELECT question FROM mock_interview_turns t JOIN mock_interview_sessions s ON s.id=t.session_id WHERE s.user_id=? AND s.role=? AND s.language=? AND t.question_number=1 ORDER BY t.id DESC LIMIT 20', (user['id'], data.role.strip(), language)).fetchall()
    prior_questions = {str(r['question']).strip().lower() for r in prior}
    if question and question.lower() in prior_questions:
        question = ''
    if not question:
        question = _resume_topic_question(data.role, data.target_goal, language, resume_text, prior_questions)
    if not question:
        bank = question_bank_for(data.role, language)
        unused = [q for q in bank if q.strip().lower() not in prior_questions]
        # Rotate fallback questions instead of always starting with item 1.
        question = (unused or bank)[int(time.time()) % len(unused or bank)]
    if not _mock_language_ok(question, language):
        question = _goal_specific_fallback(data.role, data.target_goal, language, resume_text, prior_questions)
    cur = conn.execute('INSERT INTO mock_interview_sessions(user_id,role,target_goal,language,resume_job_id,created_at) VALUES(?,?,?,?,?,?)',
                                     (user['id'], data.role.strip(), data.target_goal.strip(), language, data.resume_job_id.strip(), now()))
    sid = cur.lastrowid
    conn.execute('INSERT INTO mock_interview_turns(session_id,question_number,question,created_at) VALUES(?,?,?,?)', (sid, 1, question, now()))
    conn.commit(); conn.close()
    return {'success': True, 'session_id': sid, 'question': question, 'role': data.role.strip(), 'language': language, 'question_number': 1, 'total_questions': 10}


@features_router.post('/mocks/{session_id}/answer')
def answer_mock(session_id: int, data: MockAnswer, user=Depends(get_current_user)):
    answer = data.answer.strip()
    conn = db(); session = conn.execute('SELECT * FROM mock_interview_sessions WHERE id=? AND user_id=?', (session_id, user['id'])).fetchone()
    if not session:
        conn.close(); raise HTTPException(404, 'Mock interview session not found.')
    if session['completed'] or session['cancelled']:
        conn.close(); return {'success': True, 'final': True, 'score': session['final_score'], 'feedback': session['final_feedback'], 'question_number': 10, 'total_questions': 10}
    turn = conn.execute('SELECT * FROM mock_interview_turns WHERE session_id=? AND question_number=?', (session_id, session['current_question'])).fetchone()
    if not turn:
        conn.close(); raise HTTPException(404, 'Current interview question not found.')

    resume_text = _resume_context(session['resume_job_id'], user['id'])
    history_rows = conn.execute('SELECT question_number,question,answer,score,feedback FROM mock_interview_turns WHERE session_id=? AND answer<>"" ORDER BY question_number', (session_id,)).fetchall()
    history = '\n'.join(f"Q{r['question_number']}: {r['question']}\nA: {r['answer']}\nScore: {r['score']}" for r in history_rows)
    previous_questions = '\n'.join(r['question'] for r in conn.execute('SELECT question FROM mock_interview_turns WHERE session_id=? ORDER BY question_number', (session_id,)).fetchall())
    qnum = int(session['current_question'])
    prompt = f'''You are ResumeAI's adaptive AI interviewer.
Role: {session['role']}
Target goal: {session['target_goal'] or session['role']}
Language: {session['language']}
This is question {qnum} of exactly 10.
Evaluate the candidate's answer fairly. Use only the answer and resume evidence. Never invent facts.
IMPORTANT LANGUAGE RULE: Write ALL user-visible question, feedback, strengths, improvement and final summary text entirely in the session's selected language. Never switch to English just because the resume is in English:
- English = natural professional English.
- Hindi = natural Hindi in Devanagari script; do not use English sentences.
Then create the next question only if this is not question 10. The next question must adapt to the candidate's answer, resume and target role. It MUST be different from every question in PREVIOUS QUESTIONS and should test a new competency. Prefer a resume-specific topic when evidence exists.
Return JSON only with fields: score (integer 0-100), relevance_score (integer 0-100), feedback (string), strengths (string), improvement (string), next_question (string or empty), final_summary (string or empty), final_score (number or null).
SCORING RULE: Relevance is mandatory. If the answer does not actually address the current question at all, set relevance_score below 15 and score 0. If relevance is only weak (15-49), score no higher than 45. Do not award a high score merely because the answer is long, fluent, or grammatically correct. Evaluate both typed and spoken answers by their actual transcribed content.
For question 10, next_question must be empty and final_summary/final_score must be filled.
TARGET ROLE: {session['role']}
TARGET GOAL: {session['target_goal'] or session['role']}
RESUME:\n{resume_text}\n\nPREVIOUS QUESTIONS:\n{previous_questions}\n\nPREVIOUS ANSWERS:\n{history}\n\nCURRENT QUESTION:\n{turn['question']}\n\nCURRENT ANSWER:\n{answer}'''
    ai = _mock_ai(prompt) if resume_text else None
    if not ai:
        if session['language'] == 'Hindi':
            ai = {'score': 35, 'relevance_score': 40, 'feedback': 'उत्तर में कुछ उपयोगी जानकारी है, लेकिन इसे वर्तमान प्रश्न से अधिक सीधे जोड़ने की जरूरत है।', 'strengths': 'आपने प्रश्न का उत्तर देने का प्रयास किया।', 'improvement': 'उत्तर को प्रश्न पर केंद्रित रखें और अपने वास्तविक उदाहरण या अनुभव को स्पष्ट रूप से समझाएँ।'}
        else:
            ai = _fallback_evaluation(answer, qnum, turn['question'])
    # Gemini can occasionally ignore a language instruction. Never expose
    # that mismatch to the user; replace only the affected user-visible field.
    for key in ('feedback', 'strengths', 'improvement', 'next_question', 'final_summary'):
        value = str(ai.get(key) or '').strip()
        if value and not _mock_language_ok(value, session['language']):
            if key == 'next_question':
                ai[key] = ''
            elif key == 'final_summary':
                ai[key] = _localized_mock_fallback(session['language'], 'final')
            else:
                ai[key] = _localized_mock_fallback(session['language'], key)
    ai_score = int(max(0, min(100, float(ai.get('score', 0)))))
    quality_score, quality_message, lexical_relevance = _answer_quality(answer, turn['question'])
    try:
        ai_relevance = int(max(0, min(100, float(ai.get('relevance_score', lexical_relevance)))))
    except Exception:
        ai_relevance = lexical_relevance
    # A model must never rescue an unrelated/meaningless answer with a high score.
    # Use the stricter of AI relevance and the local relevance gate.
    relevance = min(ai_relevance, lexical_relevance)
    local_messages = {
        'Hindi': {
            'short': ('उत्तर बहुत छोटा है और इसका सही मूल्यांकन नहीं किया जा सकता।', 'उत्तर में पर्याप्त जानकारी नहीं है।', 'प्रश्न का सीधा उत्तर दें और जहाँ संभव हो अपना वास्तविक उदाहरण दें।'),
            'irrelevant': ('उत्तर वर्तमान प्रश्न का पर्याप्त उत्तर नहीं देता।', 'आपने उत्तर देने की कोशिश की, लेकिन उसे प्रश्न पर अधिक केंद्रित करने की जरूरत है।', 'पहले प्रश्न का सीधा उत्तर दें और असंबंधित जानकारी हटाएँ।'),
            'weak': ('उत्तर में कुछ संबंधित जानकारी है, लेकिन प्रश्न से इसका संबंध कमजोर है।', 'आपने प्रश्न का प्रयास किया है।', 'पहले प्रश्न के मुख्य हिस्से को सीधे address करें और फिर अतिरिक्त विवरण दें।'),
            'detail': ('उत्तर में अधिक प्रासंगिक विवरण की जरूरत है।', 'आपने उत्तर देने की कोशिश की।', 'बताएँ कि आपने क्या किया, क्यों किया और उसका परिणाम क्या रहा।')
        },
    }.get(session['language'])
    if quality_score <= 10:
        score = 0 if quality_score == 0 else quality_score
        feedback = (local_messages['short'][0] if local_messages else quality_message)
        strengths = (local_messages['short'][1] if local_messages else 'The response was submitted, but it did not contain enough meaningful interview content.')
        improvement = (local_messages['short'][2] if local_messages else 'Answer the question directly using your own words and include a real example when possible.')
    elif relevance < 15:
        score = 0
        feedback = local_messages['irrelevant'][0] if local_messages else 'The response does not answer the current question.'
        strengths = local_messages['irrelevant'][1] if local_messages else 'The answer was submitted, but it did not address the question.'
        improvement = local_messages['irrelevant'][2] if local_messages else 'Answer the exact question first and remove unrelated information.'
    elif relevance < 25:
        score = min(ai_score, 20)
        feedback = local_messages['irrelevant'][0] if local_messages else 'The response does not answer the current question closely enough.'
        strengths = local_messages['irrelevant'][1] if local_messages else 'You submitted a response, but it needs to stay focused on the interviewer’s question.'
        improvement = local_messages['irrelevant'][2] if local_messages else 'Answer the exact question first and remove unrelated information.'
    elif relevance < 50:
        score = min(ai_score, 45)
        feedback = str(ai.get('feedback') or (local_messages['weak'][0] if local_messages else 'The answer has some relevant content, but the connection to the question is weak.'))
        strengths = str(ai.get('strengths') or (local_messages['weak'][1] if local_messages else 'You attempted the question.'))
        improvement = str(ai.get('improvement') or (local_messages['weak'][2] if local_messages else 'Directly address the key part of the question before adding extra details.'))
    elif quality_score <= 30:
        score = min(ai_score, 35)
        feedback = (local_messages['detail'][0] if local_messages else quality_message) or str(ai.get('feedback') or 'The response needs more relevant detail.')
        strengths = str(ai.get('strengths') or (local_messages['detail'][1] if local_messages else 'You attempted the question.'))
        improvement = str(ai.get('improvement') or (local_messages['detail'][2] if local_messages else 'Explain what you did, why you did it, and what the result was.'))
    else:
        score = min(ai_score, max(quality_score + 15, 0))
        feedback = str(ai.get('feedback') or 'Review the answer and make your reasoning more specific.')
        strengths = str(ai.get('strengths') or '')
        improvement = str(ai.get('improvement') or '')
    conn.execute('UPDATE mock_interview_turns SET answer=?,score=?,feedback=?,strengths=?,improvement=? WHERE id=?', (answer, score, feedback, strengths, improvement, turn['id']))

    if qnum >= 10:
        scores = [r[0] for r in conn.execute('SELECT score FROM mock_interview_turns WHERE session_id=? AND score IS NOT NULL', (session_id,)).fetchall()]
        final_score = round(sum(scores) / len(scores), 1) if scores else score
        final_feedback = str(ai.get('final_summary') or 'Interview complete. Review the feedback from each answer and practice the areas that need improvement.')
        conn.execute('UPDATE mock_interview_sessions SET completed=1,final_score=?,final_feedback=? WHERE id=?', (final_score, final_feedback, session_id))
        report_rows = conn.execute('SELECT question_number,question,answer,score,feedback,strengths,improvement FROM mock_interview_turns WHERE session_id=? ORDER BY question_number', (session_id,)).fetchall()
        final_report = [dict(r) for r in report_rows]
        conn.commit(); conn.close()
        _notify_user(user['id'], 'ResumeAI — mock interview complete', f'Your 10-question AI mock interview for {session["role"]} is complete. Final score: {final_score}/100.')
        return {'success': True, 'final': True, 'final_score': final_score, 'final_feedback': final_feedback, 'final_report': final_report, 'question_number': 10, 'total_questions': 10}

    next_question = str(ai.get('next_question') or '').strip()
    used = {str(r['question']).strip().lower() for r in conn.execute('SELECT question FROM mock_interview_turns WHERE session_id=?', (session_id,)).fetchall()}
    if not next_question or next_question.lower() in used or not _mock_language_ok(next_question, session['language']):
        bank = question_bank_for(session['role'], session['language'])
        next_question = next((q for q in bank if q.strip().lower() not in used), _goal_specific_fallback(session['role'], session['target_goal'], session['language'], resume_text, used))
    next_num = qnum + 1
    conn.execute('UPDATE mock_interview_sessions SET current_question=? WHERE id=?', (next_num, session_id))
    conn.execute('INSERT INTO mock_interview_turns(session_id,question_number,question,created_at) VALUES(?,?,?,?)', (session_id, next_num, next_question, now()))
    conn.commit(); conn.close()
    return {'success': True, 'final': False, 'next_question': next_question, 'question_number': qnum, 'next_question_number': next_num, 'total_questions': 10}


@features_router.post('/mocks/{session_id}/cancel')
def cancel_mock(session_id: int, user=Depends(get_current_user)):
    conn = db()
    session = conn.execute('SELECT * FROM mock_interview_sessions WHERE id=? AND user_id=?', (session_id, user['id'])).fetchone()
    if not session:
        conn.close(); raise HTTPException(404, 'Mock interview session not found.')
    conn.execute('UPDATE mock_interview_sessions SET cancelled=1 WHERE id=? AND user_id=?', (session_id, user['id']))
    conn.commit(); conn.close()
    return {'success': True, 'message': 'Mock interview ended. Your completed answers remain saved.'}


@features_router.get('/mocks')
def mock_history(user=Depends(get_current_user)):
    conn = db(); rows = conn.execute('SELECT * FROM mock_interview_sessions WHERE user_id=? ORDER BY id DESC LIMIT 30', (user['id'],)).fetchall(); conn.close()
    return {'success': True, 'sessions': [dict(r) for r in rows]}


@features_router.get('/mocks/{session_id}/details')
def mock_details(session_id: int, user=Depends(get_current_user)):
    conn = db(); session = conn.execute('SELECT * FROM mock_interview_sessions WHERE id=? AND user_id=?', (session_id, user['id'])).fetchone(); turns = conn.execute('SELECT * FROM mock_interview_turns WHERE session_id=? ORDER BY question_number', (session_id,)).fetchall() if session else []
    conn.close()
    if not session: raise HTTPException(404, 'Mock interview session not found.')
    return {'success': True, 'session': dict(session), 'turns': [dict(r) for r in turns]}


@features_router.get('/jobs')
def jobs(
    search: str = '', limit: int = 30, resume_job_id: str = '', role_filter: str = '',
    skill_filter: str = '', location_filter: str = '', experience_filter: str = '',
    work_mode: str = 'Any', country: str = 'Any country', user=Depends(get_current_user),
):
    resume_text = _resume_context(resume_job_id, user['id'])
    profile = _resume_profile_for_jobs(resume_text)
    search_value = search.strip().lower()
    wanted_country = country.strip().lower()
    wanted_location = location_filter.strip().lower()

    def level_for(text):
        t=text.lower()
        if re.search(r'\b(senior|sr\.?|lead|principal|staff|manager|director|head)\b', t): return 'Senior level'
        if re.search(r'\b(mid|middle|intermediate)\b', t): return 'Mid level'
        if re.search(r'\b(junior|jr\.?|entry|intern|internship|graduate|fresher|trainee)\b', t): return 'Entry level'
        return 'Any experience'

    def normalize(item):
        title=str(item.get('title') or '').strip(); company=str(item.get('company') or '').strip(); location=str(item.get('location') or '').strip()
        desc=str(item.get('description') or '')
        text=' '.join([title, company, location, desc, str(item.get('category') or ''), str(item.get('job_type') or '')])
        remote=bool(item.get('remote')) or 'remote' in text.lower() or 'work from home' in text.lower()
        mode='Remote' if remote else 'On-site'
        if 'hybrid' in text.lower(): mode='Hybrid'
        return {**item, 'title':title, 'company':company or 'Company not listed', 'location':location or ('Remote / Worldwide' if remote else 'Location not listed'), 'description':desc, 'work_mode':mode, 'experience_level':level_for(text)}

    def fetch_json(url, source):
        try:
            req=urllib.request.Request(url, headers={'User-Agent':'ResumeAI/3.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode('utf-8')), source
        except Exception as exc:
            print(f'Jobs provider {source} error:', repr(exc)); return None, source

    collected=[]; sources=[]
    # Remotive: strong remote/global coverage.
    payload, source = fetch_json('https://remotive.com/api/remote-jobs?limit=100', 'Remotive')
    if payload:
        sources.append(source)
        for j in payload.get('jobs', []):
            collected.append(normalize({'id':f"remotive:{j.get('id')}", 'title':j.get('title'), 'company':j.get('company_name'), 'location':j.get('candidate_required_location'), 'url':j.get('url'), 'publication_date':j.get('publication_date'), 'source':'Remotive', 'category':j.get('category'), 'job_type':j.get('job_type'), 'description':j.get('description'), 'remote':True}))
    # Arbeitnow: free no-key feed with jobs from multiple ATS sources, especially Europe/UK.
    for api_url, src in [('https://www.arbeitnow.com/api/job-board-api','Arbeitnow'),('https://www.arbeitnow.co.uk/api/job-board-api','Arbeitnow UK')]:
        payload, _ = fetch_json(api_url, src)
        if payload:
            sources.append(src)
            for j in payload.get('data', []):
                collected.append(normalize({'id':f"arbeitnow:{j.get('slug') or j.get('id')}", 'title':j.get('title'), 'company':j.get('company_name') or j.get('company'), 'location':j.get('location'), 'url':j.get('url'), 'publication_date':j.get('created_at') or j.get('created'), 'source':'Arbeitnow', 'category':j.get('category'), 'job_type':j.get('job_types'), 'description':j.get('description'), 'remote':j.get('remote')}))
    # Adzuna is optional but dramatically increases country coverage. Configure app id/key in .env.
    adzuna_id=os.getenv('ADZUNA_APP_ID','').strip(); adzuna_key=os.getenv('ADZUNA_APP_KEY','').strip()
    countries={'India':'in','United Kingdom':'gb','USA':'us','Canada':'ca','Australia':'au','Germany':'de','France':'fr','Netherlands':'nl','Singapore':'sg','New Zealand':'nz','South Africa':'za','Poland':'pl','Italy':'it','Spain':'es','Brazil':'br','Mexico':'mx','Austria':'at','Belgium':'be','Switzerland':'ch'}
    country_codes=[countries[wanted_country.title()]] if wanted_country.title() in countries else list(countries.values()) if wanted_country in ('','any country','worldwide') else []
    if adzuna_id and adzuna_key and country_codes:
        query=search.strip() or (profile['roles'][0] if profile['roles'] else 'software developer')
        for code in country_codes[:8]:
            url='https://api.adzuna.com/v1/api/jobs/{}/search/1?{}'.format(code, urllib.parse.urlencode({'app_id':adzuna_id,'app_key':adzuna_key,'results_per_page':40,'what':query,'content-type':'application/json'}))
            payload, _ = fetch_json(url, 'Adzuna')
            if payload:
                if 'Adzuna' not in sources: sources.append('Adzuna')
                for j in payload.get('results', []):
                    loc=(j.get('location') or {}).get('display_name','') if isinstance(j.get('location'),dict) else str(j.get('location') or '')
                    collected.append(normalize({'id':f"adzuna:{j.get('id')}", 'title':j.get('title'), 'company':(j.get('company') or {}).get('display_name','') if isinstance(j.get('company'),dict) else j.get('company'), 'location':loc, 'url':j.get('redirect_url'), 'publication_date':j.get('created'), 'source':'Adzuna', 'category':(j.get('category') or {}).get('label','') if isinstance(j.get('category'),dict) else '', 'job_type':j.get('contract_type'), 'description':j.get('description'), 'remote':False}))

    # Deduplicate by title/company/location/url.
    seen=set(); out=[]
    for item in collected:
        key=re.sub(r'\W+',' ', ' '.join([item.get('title',''),item.get('company',''),item.get('location','')]).lower()).strip()
        if key in seen: continue
        seen.add(key)
        hay=(item.get('title','')+' '+item.get('company','')+' '+item.get('location','')+' '+item.get('description','')+' '+str(item.get('category',''))).lower()
        terms=[w for w in re.findall(r'[a-z0-9]+',search_value) if len(w)>2]
        if terms and not any(t in hay for t in terms): continue
        if role_filter and role_filter.lower() not in hay: continue
        if skill_filter and skill_filter.lower() not in hay: continue
        if wanted_location and wanted_location not in hay: continue
        if wanted_country and wanted_country not in ('any country','worldwide') and wanted_country not in hay:
            # India/USA aliases.
            aliases={'india':['india'],'usa':['usa','united states','us'],'uk':['uk','united kingdom','england','london']}
            if not any(a in hay for a in aliases.get(wanted_country, [wanted_country])): continue
        if work_mode and work_mode!='Any' and item['work_mode'] != work_mode: continue
        if experience_filter and experience_filter!='Any experience' and item['experience_level'] != experience_filter: continue
        item['match_score']=_job_match(item, profile, search_value) if resume_text else 0
        if item['match_score'] == 0 and resume_text and not search_value:
            item['match_score']=max(5, min(25, _job_match(item, {'roles':profile['roles'][:1], 'skills':profile['skills'][:5]}, '')))
        out.append(item)
    out.sort(key=lambda x:(-int(x.get('match_score',0)), str(x.get('publication_date') or '')), reverse=False)
    countries_out=['Any country']+list(countries.keys())
    return {'success':True,'jobs':out[:max(1,min(limit,60))],'sources':sources,'source':', '.join(dict.fromkeys(sources)) or 'No live provider responded','resume_matching':bool(resume_text),'filters':{'roles':profile['roles'],'skills':profile['skills'],'locations':['Remote','Worldwide','India','USA','United Kingdom','Europe','Asia','Canada','Australia'],'countries':countries_out,'experience':['Any experience','Entry level','Mid level','Senior level'],'work_modes':['Any','Remote','Hybrid','On-site']}}


@features_router.get('/dashboard')
def dashboard(user=Depends(get_current_user)):
    conn = db()
    total = conn.execute('SELECT COUNT(*) c FROM resume_analyses WHERE user_id=?', (user['id'],)).fetchone()['c']
    latest = conn.execute('SELECT score, filename, created_at FROM resume_analyses WHERE user_id=? ORDER BY id DESC LIMIT 1', (user['id'],)).fetchone()
    mocks = conn.execute('SELECT COUNT(*) c, AVG(final_score) avg FROM mock_interview_sessions WHERE user_id=? AND completed=1 AND cancelled=0', (user['id'],)).fetchone()
    apps = conn.execute('SELECT COUNT(*) c FROM applications WHERE user_id=?', (user['id'],)).fetchone()['c']
    conn.close()
    return {'success': True, 'dashboard': {'total_resumes': total, 'latest_score': latest['score'] if latest else None, 'latest_filename': latest['filename'] if latest else None, 'latest_analyzed_at': latest['created_at'] if latest else None, 'mock_interviews': mocks['c'] or 0, 'applications': apps, 'average_mock_score': round(mocks['avg'], 1) if mocks['avg'] is not None else None}}


@features_router.get('/resume-history')
def resume_history(user=Depends(get_current_user)):
    conn = db()
    rows = conn.execute('SELECT id,filename,score,created_at,analysis_json FROM resume_analyses WHERE user_id=? ORDER BY id DESC LIMIT 50', (user['id'],)).fetchall()
    conn.close()
    out=[]
    for row in rows:
        item=dict(row); item['analysis']=json.loads(item.pop('analysis_json'))
        out.append(item)
    return {'success': True, 'history': out}


@features_router.get('/analytics')
def analytics(user=Depends(get_current_user)):
    conn = db(); apps = conn.execute('SELECT COUNT(*) c FROM applications WHERE user_id=?', (user['id'],)).fetchone()['c']; mocks = conn.execute('SELECT COUNT(*) c, AVG(final_score) avg FROM mock_interview_sessions WHERE user_id=? AND completed=1', (user['id'],)).fetchone(); conn.close()
    return {'success': True, 'analytics': {'applications': apps, 'mock_interviews': mocks['c'] or 0, 'average_mock_score': round(mocks['avg'], 1) if mocks['avg'] is not None else None}}


@features_router.get('/premium/status')
def premium_status(user=Depends(get_current_user)):
    return {'success': True, 'premium': True, 'message': 'Advanced ResumeAI tools are enabled in this build. No payment is required to use the project build.'}

# ---------------------------------------------------------
# Daily notification digest worker
# ---------------------------------------------------------
def send_due_notification_digests():
    now_dt = datetime.now(timezone.utc)
    conn = db()
    users = conn.execute("SELECT id,email,name FROM users WHERE email NOT LIKE '%@guest.resumeai.local'").fetchall()
    for user in users:
        if not _email_notifications_enabled(user['id']):
            continue
        last = conn.execute('SELECT last_sent_at FROM notification_digest_log WHERE user_id=?', (user['id'],)).fetchone()
        if last and last['last_sent_at']:
            try:
                if (now_dt - datetime.fromisoformat(last['last_sent_at'])).total_seconds() < 86400:
                    continue
            except Exception:
                pass
        events = conn.execute('SELECT title,body FROM notification_events WHERE user_id=? ORDER BY id DESC LIMIT 5', (user['id'],)).fetchall()
        body_lines = [
            f"Hi {user['name']},",
            "",
            "Here is your ResumeAI career digest:",
            "• ResumeAI improvements: resume analysis, grounded AI feedback and career tools continue to be refined.",
            "• Resume help: revisit your latest analysis and focus on the highest-priority suggestions.",
            "• Jobs: check live job matches and update your filters for role, country and work mode.",
        ]
        if events:
            body_lines += ["", "Recent activity:"]
            body_lines += [f"• {e['title']}: {e['body']}" for e in events]
        body_lines += ["", "You can disable email notifications anytime in ResumeAI Settings.", "", "— ResumeAI"]
        sent = _send_email(user['email'], 'ResumeAI — your career digest', '\n'.join(body_lines))
        if sent:
            conn.execute('INSERT INTO notification_digest_log(user_id,last_sent_at) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET last_sent_at=excluded.last_sent_at', (user['id'], now_dt.isoformat()))
    conn.commit(); conn.close()


def notification_worker():
    # Enabled by default for a single-process local/Render deployment. If the
    # platform runs multiple workers, set RESUMEAI_NOTIFICATION_WORKER=false on
    # all but one worker to avoid duplicate sends.
    enabled = os.getenv('RESUMEAI_NOTIFICATION_WORKER', 'true').lower() in {'1','true','yes','on'}
    if not enabled:
        return
    while True:
        try:
            send_due_notification_digests()
        except Exception as exc:
            print('ResumeAI digest worker error:', repr(exc))
        time.sleep(6 * 60 * 60)

try:
    threading.Thread(target=notification_worker, name='resumeai-notification-worker', daemon=True).start()
except Exception as exc:
    print('ResumeAI notification worker startup error:', repr(exc))

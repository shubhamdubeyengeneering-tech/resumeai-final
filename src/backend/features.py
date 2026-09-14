import json, os, sqlite3, urllib.parse, urllib.request, smtplib, ssl, re
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
    if not _email_notifications_enabled(user_id):
        return
    conn = db()
    row = conn.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if row and row['email'] and '@' in row['email']:
        _send_email(row['email'], subject, body)


def init_feature_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY, phone TEXT DEFAULT '', location TEXT DEFAULT '', headline TEXT DEFAULT '', bio TEXT DEFAULT '', skills TEXT DEFAULT '', updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, email_notifications INTEGER DEFAULT 1, weekly_summary INTEGER DEFAULT 1, language TEXT DEFAULT 'English', theme TEXT DEFAULT 'system', voice_enabled INTEGER DEFAULT 1, voice_gender TEXT DEFAULT 'female', updated_at TEXT NOT NULL)''')
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
    mock_cols = {r[1] for r in conn.execute('PRAGMA table_info(mock_interview_sessions)').fetchall()}
    if 'cancelled' not in mock_cols:
        conn.execute("ALTER TABLE mock_interview_sessions ADD COLUMN cancelled INTEGER DEFAULT 0")
    conn.commit(); conn.close()


init_feature_db()


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    return get_db()


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(default='', max_length=30)
    location: str = Field(default='', max_length=120)
    headline: str = Field(default='', max_length=160)
    bio: str = Field(default='', max_length=1000)
    skills: str = Field(default='', max_length=1000)


class SettingsUpdate(BaseModel):
    email_notifications: bool = True
    weekly_summary: bool = True
    language: str = 'English'
    theme: str = 'system'
    voice_enabled: bool = True
    voice_gender: str = 'female'


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
        return {'success': True, 'profile': {'name': user['name'], 'email': user['email'], 'phone': '', 'location': '', 'headline': '', 'bio': '', 'skills': ''}}
    d = dict(row); d.pop('user_id', None); d.pop('updated_at', None)
    return {'success': True, 'profile': {'name': user['name'], 'email': user['email'], **d}}


@features_router.put('/profile')
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    conn = db(); ts = now()
    conn.execute('''INSERT INTO profiles(user_id,phone,location,headline,bio,skills,updated_at) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone,location=excluded.location,headline=excluded.headline,bio=excluded.bio,skills=excluded.skills,updated_at=excluded.updated_at''',
                 (user['id'], data.phone.strip(), data.location.strip(), data.headline.strip(), data.bio.strip(), data.skills.strip(), ts))
    conn.execute('UPDATE users SET name=? WHERE id=?', (data.name.strip(), user['id'])); conn.commit(); conn.close()
    return {'success': True, 'message': 'Profile saved.'}


@features_router.get('/settings')
def get_settings(user=Depends(get_current_user)):
    conn = db(); row = conn.execute('SELECT * FROM settings WHERE user_id=?', (user['id'],)).fetchone(); conn.close()
    if not row:
        return {'success': True, 'settings': {'email_notifications': True, 'weekly_summary': True, 'language': 'English', 'theme': 'system', 'voice_enabled': True, 'voice_gender': 'female'}}
    d = dict(row)
    return {'success': True, 'settings': {'email_notifications': bool(d['email_notifications']), 'weekly_summary': bool(d['weekly_summary']), 'language': d['language'], 'theme': d.get('theme') or 'system', 'voice_enabled': bool(d.get('voice_enabled', 1)), 'voice_gender': d.get('voice_gender') or 'female'}}


@features_router.put('/settings')
def update_settings(data: SettingsUpdate, user=Depends(get_current_user)):
    language = data.language if data.language in {'English', 'Hindi', 'Hinglish'} else 'English'
    theme = data.theme if data.theme in {'system', 'light', 'dark'} else 'system'
    voice_gender = data.voice_gender if data.voice_gender in {'female', 'male'} else 'female'
    conn = db(); ts = now()
    conn.execute('''INSERT INTO settings(user_id,email_notifications,weekly_summary,language,theme,voice_enabled,voice_gender,updated_at) VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET email_notifications=excluded.email_notifications,weekly_summary=excluded.weekly_summary,language=excluded.language,theme=excluded.theme,voice_enabled=excluded.voice_enabled,voice_gender=excluded.voice_gender,updated_at=excluded.updated_at''',
                 (user['id'], int(data.email_notifications), int(data.weekly_summary), language, theme, int(data.voice_enabled), voice_gender, ts))
    conn.commit(); conn.close()
    return {'success': True, 'message': 'Settings saved.'}


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


def question_bank_for(role: str):
    r = role.lower()
    if any(x in r for x in ['software', 'developer', 'frontend', 'backend', 'full stack', 'engineer', 'web']):
        return QUESTION_BANK['software']
    if any(x in r for x in ['data', 'analyst', 'analytics']):
        return QUESTION_BANK['data']
    return QUESTION_BANK['default']


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
            config=types.GenerateContentConfig(temperature=0.35, response_mime_type='application/json')
        )
        raw = (response.text or '').strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            raw = raw.replace('json\n', '', 1).strip()
        return json.loads(raw)
    except Exception as exc:
        print('Mock AI error:', repr(exc))
        return None


def _resume_context(resume_job_id: str):
    if not resume_job_id:
        return ''
    try:
        from main import ai_jobs
        job = ai_jobs.get(resume_job_id) or {}
        return (job.get('resume_text') or '')[:16000]
    except Exception:
        return ''


def _answer_quality(answer: str, question: str = ''):
    text = re.sub(r'\s+', ' ', (answer or '').strip())
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())
    if not words:
        return 0, 'The answer is empty or contains no readable words.'
    compact = re.sub(r'[^a-z0-9]+', '', text.lower())
    unique_ratio = len(set(words)) / max(1, len(words))
    alpha_ratio = sum(ch.isalpha() for ch in text) / max(1, len(text))
    repeated = bool(re.search(r'(.)\1{4,}', compact))
    filler = {'asdf', 'qwerty', 'test', 'hello', 'hi', 'abc', 'xyz', 'bahifi', 'blah', 'none', 'nothing'}
    if len(words) <= 2:
        return 8, 'The answer is too short to evaluate meaningfully.'
    if compact in filler or (len(words) <= 4 and unique_ratio < 0.65):
        return 6, 'The answer does not provide enough meaningful content.'
    if repeated or alpha_ratio < 0.45 or (any(ch.isdigit() for ch in text) and len(words) <= 2):
        return 5, 'The answer appears to contain mostly noise rather than an interview response.'
    if len(words) < 6:
        return 25, 'The answer has some content, but it needs more explanation or a concrete example.'

    q_words = set(re.findall(r"[a-z]{4,}", (question or '').lower())) - {
        'what','when','where','which','would','could','should','have','your','this','that','about','from','with','tell','walk','describe','explain'}
    overlap = len(q_words & set(words))
    relevance = 0 if not q_words else min(1.0, overlap / max(2, min(5, len(q_words))))
    score = 48
    score += min(20, len(words) * 0.8)
    score += int(unique_ratio * 10)
    score += int(alpha_ratio * 5)
    if relevance >= 0.5:
        score += 12
    elif relevance == 0 and len(words) < 15:
        score -= 15
    if any(k in words for k in ['example','because','result','impact','built','implemented','solved','learned','improved','measured','achieved']):
        score += 8
    return max(20, min(92, int(score))), ''


def _fallback_evaluation(answer: str, question_number: int, question: str = ''):
    score, gate_message = _answer_quality(answer, question)
    if score <= 10:
        return {'score': score, 'feedback': gate_message, 'strengths': 'The response was submitted, but it did not contain enough meaningful interview content.', 'improvement': 'Answer the question directly using your own words and include a real example when possible.'}
    if score <= 30:
        return {'score': score, 'feedback': gate_message or 'The response needs more relevant detail.', 'strengths': 'You attempted the question.', 'improvement': 'Explain what you did, why you did it, and what the result was.'}
    feedback = 'Add a concrete example, your specific action, and the real result if you can support it.' if score < 72 else 'Good structure. Keep the answer specific, evidence-based, and concise.'
    return {'score': score, 'feedback': feedback, 'strengths': 'The response contains meaningful content.', 'improvement': 'Use a specific situation, action, and result where applicable.'}


@features_router.post('/mocks/start')
def start_mock(data: MockStart, user=Depends(get_current_user)):
    language = data.language if data.language in {'English', 'Hindi', 'Hinglish'} else 'English'
    questions = question_bank_for(data.role)
    resume_text = _resume_context(data.resume_job_id)
    prompt = f'''You are ResumeAI's AI interviewer. Start a 10-question adaptive mock interview.
Role: {data.role.strip()}
Language: {language}
Ask exactly one first question. Use the resume as evidence when available. Do not invent experience.
If the resume is missing, ask a role-relevant question that lets the candidate explain real experience.
Return JSON only: {{"question":"..."}}.
RESUME:\n{resume_text}'''
    ai = _mock_ai(prompt)
    question = (ai or {}).get('question') or questions[0]
    conn = db(); cur = conn.execute('INSERT INTO mock_interview_sessions(user_id,role,language,resume_job_id,created_at) VALUES(?,?,?,?,?)',
                                     (user['id'], data.role.strip(), language, data.resume_job_id.strip(), now()))
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

    resume_text = _resume_context(session['resume_job_id'])
    history_rows = conn.execute('SELECT question_number,question,answer,score,feedback FROM mock_interview_turns WHERE session_id=? AND answer<>"" ORDER BY question_number', (session_id,)).fetchall()
    history = '\n'.join(f"Q{r['question_number']}: {r['question']}\nA: {r['answer']}\nScore: {r['score']}" for r in history_rows)
    qnum = int(session['current_question'])
    prompt = f'''You are ResumeAI's adaptive AI interviewer.
Role: {session['role']}
Language: {session['language']}
This is question {qnum} of exactly 10.
Evaluate the candidate's answer fairly. Use only the answer and resume evidence. Never invent facts.
Then create the next question only if this is not question 10. The next question should adapt to the candidate's answer and resume.
Return JSON only with fields: score (integer 0-100), feedback (string), strengths (string), improvement (string), next_question (string or empty), final_summary (string or empty), final_score (number or null).
For question 10, next_question must be empty and final_summary/final_score must be filled.
RESUME:\n{resume_text}\n\nPREVIOUS ANSWERS:\n{history}\n\nCURRENT QUESTION:\n{turn['question']}\n\nCURRENT ANSWER:\n{answer}'''
    ai = _mock_ai(prompt) or _fallback_evaluation(answer, qnum, turn['question'])
    ai_score = int(max(0, min(100, float(ai.get('score', 0)))))
    quality_score, quality_message = _answer_quality(answer, turn['question'])
    # A model must never rescue meaningless input with a high score.
    if quality_score <= 10:
        score = quality_score
        feedback = quality_message
        strengths = 'The response was submitted, but it did not contain enough meaningful interview content.'
        improvement = 'Answer the question directly using your own words and include a real example when possible.'
    elif quality_score <= 30:
        score = min(ai_score, 35)
        feedback = quality_message or str(ai.get('feedback') or 'The response needs more relevant detail.')
        strengths = str(ai.get('strengths') or 'You attempted the question.')
        improvement = str(ai.get('improvement') or 'Explain what you did, why you did it, and what the result was.')
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
        conn.commit(); conn.close()
        _notify_user(user['id'], 'ResumeAI — mock interview complete', f'Your 10-question AI mock interview for {session["role"]} is complete. Final score: {final_score}/100.')
        return {'success': True, 'score': score, 'feedback': feedback, 'strengths': strengths, 'improvement': improvement, 'final': True, 'final_score': final_score, 'final_feedback': final_feedback, 'question_number': 10, 'total_questions': 10}

    next_question = str(ai.get('next_question') or '').strip()
    if not next_question:
        bank = question_bank_for(session['role']); next_question = bank[min(qnum, len(bank) - 1)]
    next_num = qnum + 1
    conn.execute('UPDATE mock_interview_sessions SET current_question=? WHERE id=?', (next_num, session_id))
    conn.execute('INSERT INTO mock_interview_turns(session_id,question_number,question,created_at) VALUES(?,?,?,?)', (session_id, next_num, next_question, now()))
    conn.commit(); conn.close()
    return {'success': True, 'score': score, 'feedback': feedback, 'strengths': strengths, 'improvement': improvement, 'final': False, 'next_question': next_question, 'question_number': qnum, 'next_question_number': next_num, 'total_questions': 10}


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
def jobs(search: str = '', limit: int = 12, user=Depends(get_current_user)):
    params = urllib.parse.urlencode({'search': search.strip()}) if search.strip() else ''
    url = 'https://remotive.com/api/remote-jobs' + (('?' + params) if params else '')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ResumeAI/1.0'})
        with urllib.request.urlopen(req, timeout=12) as r: payload = json.loads(r.read().decode('utf-8'))
        out = []
        for j in payload.get('jobs', [])[:max(1, min(limit, 30))]:
            out.append({'id': j.get('id'), 'title': j.get('title'), 'company': j.get('company_name'), 'location': j.get('candidate_required_location'), 'url': j.get('url'), 'publication_date': j.get('publication_date'), 'source': 'Remotive'})
        return {'success': True, 'jobs': out, 'source': 'Remotive'}
    except Exception as exc:
        raise HTTPException(502, f'Live jobs service is temporarily unavailable: {exc}')


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

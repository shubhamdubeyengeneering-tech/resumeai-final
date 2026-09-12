import json, os, sqlite3, urllib.parse, urllib.request
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user, get_db

features_router = APIRouter(prefix='/api', tags=['ResumeAI Workspace'])

def init_feature_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY, phone TEXT DEFAULT '', location TEXT DEFAULT '', headline TEXT DEFAULT '', bio TEXT DEFAULT '', skills TEXT DEFAULT '', updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, email_notifications INTEGER DEFAULT 1, weekly_summary INTEGER DEFAULT 1, language TEXT DEFAULT 'English', updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, company TEXT NOT NULL, role TEXT NOT NULL, location TEXT DEFAULT '', url TEXT DEFAULT '', status TEXT DEFAULT 'Applied', notes TEXT DEFAULT '', applied_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, role TEXT NOT NULL, question TEXT NOT NULL, answer TEXT DEFAULT '', score INTEGER, feedback TEXT DEFAULT '', created_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS resume_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        score INTEGER NOT NULL,
        analysis_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    conn.commit(); conn.close()
init_feature_db()

def now(): return datetime.now(timezone.utc).isoformat()
def db(): return get_db()

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
class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=180)
    location: str = Field(default='', max_length=150)
    url: str = Field(default='', max_length=1000)
    status: str = 'Applied'
    notes: str = Field(default='', max_length=2000)
class ApplicationUpdate(BaseModel):
    company: str | None = None; role: str | None = None; location: str | None = None; url: str | None = None; status: str | None = None; notes: str | None = None
class MockStart(BaseModel): role: str = Field(min_length=2, max_length=100)
class MockAnswer(BaseModel): answer: str = Field(min_length=2, max_length=4000)

@features_router.get('/me')
def me(user=Depends(get_current_user)): return {'success': True, 'user': user}

@features_router.get('/profile')
def get_profile(user=Depends(get_current_user)):
    conn=db(); row=conn.execute('SELECT * FROM profiles WHERE user_id=?',(user['id'],)).fetchone(); conn.close()
    if not row: return {'success':True,'profile':{'name':user['name'],'email':user['email'],'phone':'','location':'','headline':'','bio':'','skills':''}}
    d=dict(row); d.pop('user_id',None); return {'success':True,'profile':{'name':user['name'],'email':user['email'],**d}}

@features_router.put('/profile')
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    conn=db(); ts=now()
    conn.execute('''INSERT INTO profiles(user_id,phone,location,headline,bio,skills,updated_at) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone,location=excluded.location,headline=excluded.headline,bio=excluded.bio,skills=excluded.skills,updated_at=excluded.updated_at''',
                 (user['id'],data.phone.strip(),data.location.strip(),data.headline.strip(),data.bio.strip(),data.skills.strip(),ts))
    conn.execute('UPDATE users SET name=? WHERE id=?',(data.name.strip(),user['id'])); conn.commit(); conn.close()
    return {'success':True,'message':'Profile saved.'}

@features_router.get('/settings')
def get_settings(user=Depends(get_current_user)):
    conn=db(); row=conn.execute('SELECT * FROM settings WHERE user_id=?',(user['id'],)).fetchone(); conn.close()
    if not row: return {'success':True,'settings':{'email_notifications':True,'weekly_summary':True,'language':'English'}}
    d=dict(row); return {'success':True,'settings':{'email_notifications':bool(d['email_notifications']),'weekly_summary':bool(d['weekly_summary']),'language':d['language']}}

@features_router.put('/settings')
def update_settings(data: SettingsUpdate,user=Depends(get_current_user)):
    conn=db(); ts=now(); conn.execute('''INSERT INTO settings(user_id,email_notifications,weekly_summary,language,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET email_notifications=excluded.email_notifications,weekly_summary=excluded.weekly_summary,language=excluded.language,updated_at=excluded.updated_at''',(user['id'],int(data.email_notifications),int(data.weekly_summary),data.language,ts)); conn.commit(); conn.close(); return {'success':True,'message':'Settings saved.'}

@features_router.get('/applications')
def list_applications(user=Depends(get_current_user)):
    conn=db(); rows=conn.execute('SELECT * FROM applications WHERE user_id=? ORDER BY id DESC',(user['id'],)).fetchall(); conn.close(); return {'success':True,'applications':[dict(r) for r in rows]}

@features_router.post('/applications')
def add_application(data: ApplicationCreate,user=Depends(get_current_user)):
    conn=db(); cur=conn.execute('INSERT INTO applications(user_id,company,role,location,url,status,notes,applied_at) VALUES(?,?,?,?,?,?,?,?)',(user['id'],data.company.strip(),data.role.strip(),data.location.strip(),data.url.strip(),data.status.strip(),data.notes.strip(),now())); conn.commit(); row=conn.execute('SELECT * FROM applications WHERE id=?',(cur.lastrowid,)).fetchone(); conn.close(); return {'success':True,'application':dict(row)}

@features_router.patch('/applications/{application_id}')
def edit_application(application_id:int,data:ApplicationUpdate,user=Depends(get_current_user)):
    conn=db(); row=conn.execute('SELECT * FROM applications WHERE id=? AND user_id=?',(application_id,user['id'])).fetchone()
    if not row: conn.close(); raise HTTPException(404,'Application not found.')
    fields=[]; vals=[]
    for key in ['company','role','location','url','status','notes']:
        val=getattr(data,key)
        if val is not None: fields.append(f'{key}=?'); vals.append(val.strip() if isinstance(val,str) else val)
    if fields: vals += [application_id,user['id']]; conn.execute(f"UPDATE applications SET {','.join(fields)} WHERE id=? AND user_id=?",vals); conn.commit()
    row=conn.execute('SELECT * FROM applications WHERE id=?',(application_id,)).fetchone(); conn.close(); return {'success':True,'application':dict(row)}

@features_router.delete('/applications/{application_id}')
def delete_application(application_id:int,user=Depends(get_current_user)):
    conn=db(); cur=conn.execute('DELETE FROM applications WHERE id=? AND user_id=?',(application_id,user['id'])); conn.commit(); conn.close()
    if cur.rowcount==0: raise HTTPException(404,'Application not found.')
    return {'success':True}

QUESTIONS = {
 'software engineer':['Tell me about a project you built. What problem did it solve?','How would you debug a production issue?','Describe a time you improved performance or reliability.'],
 'data analyst':['Walk me through an analysis you completed.','How do you handle missing or inconsistent data?','Tell me about a metric you used to make a decision.'],
 'default':['Tell me about yourself and your career goals.','Describe a challenging project and what you learned.','Why are you a good fit for this role?']}

def questions_for(role):
    r=role.lower(); key='software engineer' if 'software' in r or 'developer' in r else ('data analyst' if 'data' in r else 'default'); return QUESTIONS[key]

@features_router.post('/mocks/start')
def start_mock(data:MockStart,user=Depends(get_current_user)):
    q=questions_for(data.role)[0]; conn=db(); cur=conn.execute('INSERT INTO mock_sessions(user_id,role,question,created_at) VALUES(?,?,?,?)',(user['id'],data.role.strip(),q,now())); conn.commit(); sid=cur.lastrowid; conn.close(); return {'success':True,'session_id':sid,'question':q,'role':data.role.strip()}

@features_router.post('/mocks/{session_id}/answer')
def answer_mock(session_id:int,data:MockAnswer,user=Depends(get_current_user)):
    answer=data.answer.strip(); words=len(answer.split()); score=max(20,min(100,35 + min(words,90)//2 + (15 if any(x in answer.lower() for x in ['result','impact','improved','built','learned','metric']) else 0)))
    feedback='Good structure. Add a specific action and measurable result if your real experience supports it.' if score<75 else 'Strong answer structure. Keep it specific, concise, and evidence-based.'
    conn=db(); row=conn.execute('SELECT * FROM mock_sessions WHERE id=? AND user_id=?',(session_id,user['id'])).fetchone()
    if not row: conn.close(); raise HTTPException(404,'Mock session not found.')
    conn.execute('UPDATE mock_sessions SET answer=?,score=?,feedback=? WHERE id=?',(answer,score,feedback,session_id)); conn.commit(); conn.close(); return {'success':True,'score':score,'feedback':feedback}

@features_router.get('/mocks')
def mock_history(user=Depends(get_current_user)):
    conn=db(); rows=conn.execute('SELECT * FROM mock_sessions WHERE user_id=? ORDER BY id DESC LIMIT 30',(user['id'],)).fetchall(); conn.close(); return {'success':True,'sessions':[dict(r) for r in rows]}

@features_router.get('/jobs')
def jobs(search:str='',limit:int=12,user=Depends(get_current_user)):
    # Remotive public API: listings are delayed and must be attributed to Remotive.
    params=urllib.parse.urlencode({'search':search.strip()}) if search.strip() else ''
    url='https://remotive.com/api/remote-jobs'+(('?'+params) if params else '')
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'ResumeAI/1.0'})
        with urllib.request.urlopen(req,timeout=12) as r: payload=json.loads(r.read().decode('utf-8'))
        out=[]
        for j in payload.get('jobs',[])[:max(1,min(limit,30))]:
            out.append({'id':j.get('id'),'title':j.get('title'),'company':j.get('company_name'),'location':j.get('candidate_required_location'),'url':j.get('url'),'publication_date':j.get('publication_date'),'source':'Remotive'})
        return {'success':True,'jobs':out,'source':'Remotive'}
    except Exception as exc:
        raise HTTPException(502, f'Live jobs service is temporarily unavailable: {exc}')


# =========================================================
# RESUME HISTORY / DASHBOARD
# =========================================================

def save_resume_analysis(user_id: int, filename: str, score: int, analysis: dict):
    conn = db()
    conn.execute(
        "INSERT INTO resume_analyses(user_id, filename, score, analysis_json, created_at) VALUES(?,?,?,?,?)",
        (user_id, filename, int(score), json.dumps(analysis, ensure_ascii=False), now()),
    )
    conn.commit()
    conn.close()

@features_router.get('/dashboard')
def dashboard(user=Depends(get_current_user)):
    conn = db()
    resume_count = conn.execute(
        "SELECT COUNT(*) AS total FROM resume_analyses WHERE user_id=?", (user['id'],)
    ).fetchone()['total']
    latest = conn.execute(
        "SELECT filename, score, created_at FROM resume_analyses WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user['id'],)
    ).fetchone()
    mock_row = conn.execute(
        "SELECT COUNT(*) AS total, AVG(score) AS avg FROM mock_sessions WHERE user_id=? AND score IS NOT NULL",
        (user['id'],)
    ).fetchone()
    app_count = conn.execute(
        "SELECT COUNT(*) AS total FROM applications WHERE user_id=?", (user['id'],)
    ).fetchone()['total']
    conn.close()
    return {
        'success': True,
        'dashboard': {
            'total_resumes': int(resume_count or 0),
            'latest_score': int(latest['score']) if latest else None,
            'latest_resume': dict(latest) if latest else None,
            'mock_interviews': int(mock_row['total'] or 0),
            'average_mock_score': round(float(mock_row['avg']), 1) if mock_row['avg'] is not None else None,
            'applications': int(app_count or 0),
        }
    }

@features_router.get('/resumes')
def resume_history(user=Depends(get_current_user)):
    conn = db()
    rows = conn.execute(
        "SELECT id, filename, score, created_at FROM resume_analyses WHERE user_id=? ORDER BY id DESC LIMIT 50",
        (user['id'],)
    ).fetchall()
    conn.close()
    return {'success': True, 'resumes': [dict(r) for r in rows]}

@features_router.get('/analytics')
def analytics(user=Depends(get_current_user)):
    conn=db(); apps=conn.execute('SELECT COUNT(*) c FROM applications WHERE user_id=?',(user['id'],)).fetchone()['c']; mocks=conn.execute('SELECT COUNT(*) c, AVG(score) avg FROM mock_sessions WHERE user_id=? AND score IS NOT NULL',(user['id'],)).fetchone(); conn.close()
    return {'success':True,'analytics':{'applications':apps,'mock_interviews':mocks['c'] or 0,'average_mock_score':round(mocks['avg'],1) if mocks['avg'] is not None else None}}

@features_router.get('/premium/status')
def premium_status(user=Depends(get_current_user)):
    return {'success':True,'premium':False,'message':'Premium payment is not configured yet. Verified payment must be connected before access is granted.'}

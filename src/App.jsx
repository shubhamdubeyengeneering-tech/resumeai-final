import { useEffect, useState } from "react";
import "./App.css";

const API_URL =
  window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "https://resumeai-docker.onrender.com";

const SECTION_LIST = [
  ["contact", "Contact"],
  ["summary", "Summary"],
  ["education", "Education"],
  ["skills", "Skills"],
  ["experience", "Experience"],
  ["internship", "Internship"],
  ["projects", "Projects"],
  ["certifications", "Certifications"],
  ["achievements", "Achievements"],
];

function getScoreInfo(score) {
  if (score >= 90) {
    return {
      className: "good",
      label: "Excellent Resume",
      emoji: "🏆",
      message:
        "Your resume is already strong. Focus on small improvements to make it even more competitive.",
    };
  }

  if (score >= 80) {
    return {
      className: "good",
      label: "Strong Resume",
      emoji: "🌟",
      message:
        "Your resume has a strong foundation with a few areas that can still be improved.",
    };
  }

  if (score >= 70) {
    return {
      className: "average",
      label: "Good Resume",
      emoji: "👍",
      message:
        "Your resume is good, but improving content quality and evidence can make it significantly stronger.",
    };
  }

  if (score >= 60) {
    return {
      className: "average",
      label: "Needs Improvement",
      emoji: "⚠️",
      message:
        "Your resume needs some important improvements before it is fully job-ready.",
    };
  }

  return {
    className: "poor",
    label: "Weak Resume",
    emoji: "🔴",
    message:
      "Your resume currently has several important gaps. Focus on the highest-priority improvements first.",
  };
}

function canonicalSections(sections) {
  if (!Array.isArray(sections)) return [];

  return sections.map((item) =>
    String(item).toLowerCase()
  );
}

function isSectionHeading(line) {
  const value = line
    .replace(/[^a-zA-Z ]/g, "")
    .trim()
    .toLowerCase();

  const headings = [
    "professional summary",
    "summary",
    "profile",
    "objective",
    "skills",
    "technical skills",
    "experience",
    "work experience",
    "professional experience",
    "internship",
    "internships",
    "projects",
    "education",
    "certifications",
    "certification",
    "achievements",
    "awards",
    "honors",
  ];

  return headings.includes(value);
}

function isBullet(line) {
  return /^(?:[•●▪◦‣*-]|\d+[.)])\s+/.test(
    line.trim()
  );
}

function renderEnhancedPreview(text) {
  if (!text) return null;

  const lines = text.split(/\r?\n/);
  let meaningfulIndex = 0;

  return lines.map((rawLine, index) => {
    const line = rawLine.trim();

    if (!line) {
      return (
        <div
          className="resume-preview-space"
          key={index}
        />
      );
    }

    const currentMeaningfulIndex =
      meaningfulIndex;

    meaningfulIndex += 1;

    if (currentMeaningfulIndex === 0) {
      return (
        <div
          className="resume-preview-name"
          key={index}
        >
          {line}
        </div>
      );
    }

    if (
      currentMeaningfulIndex === 1 &&
      (line.includes("@") ||
        line.includes("linkedin") ||
        line.includes("github") ||
        /\d{7,}/.test(line))
    ) {
      return (
        <div
          className="resume-preview-contact"
          key={index}
        >
          {line}
        </div>
      );
    }

    if (isSectionHeading(line)) {
      return (
        <div
          className="resume-preview-section"
          key={index}
        >
          {line.toUpperCase()}
        </div>
      );
    }

    if (isBullet(line)) {
      return (
        <div
          className="resume-preview-bullet"
          key={index}
        >
          <span>•</span>

          <span>
            {line.replace(
              /^(?:[•●▪◦‣*-]|\d+[.)])\s+/,
              ""
            )}
          </span>
        </div>
      );
    }

    return (
      <div
        className="resume-preview-line"
        key={index}
      >
        {line}
      </div>
    );
  });
}


function WorkspaceModules({ page, currentUser, onNavigate }) {
  const token = localStorage.getItem("resumeai_token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const [mockRole, setMockRole] = useState("Software Engineer");
  const [mockSession, setMockSession] = useState(null);
  const [mockAnswer, setMockAnswer] = useState("");
  const [mockEvaluation, setMockEvaluation] = useState(null);
  const [mockHistory, setMockHistory] = useState([]);
  const [mockFinal, setMockFinal] = useState(null);

  const [jobs, setJobs] = useState([]);
  const [jobSearch, setJobSearch] = useState("");
  const [applications, setApplications] = useState([]);
  const [appForm, setAppForm] = useState({ company: "", role: "", location: "", url: "", status: "Applied", notes: "" });

  const [profile, setProfile] = useState({ name: currentUser?.name || "", email: currentUser?.email || "", phone: "", location: "", headline: "", bio: "", skills: "" });
  const [settings, setSettings] = useState({ email_notifications: true, weekly_summary: true, language: "English" });
  const [analytics, setAnalytics] = useState(null);
  const [premium, setPremium] = useState(null);

  async function api(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...headers, ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.message || "Request failed.");
    return data;
  }

  useEffect(() => {
    if (!currentUser || !token) return;
    setMessage("");

    if (page === "applications") {
      api("/api/applications").then(d => setApplications(d.applications || [])).catch(e => setMessage(e.message));
    } else if (page === "profile") {
      api("/api/profile").then(d => setProfile(d.profile || {})).catch(e => setMessage(e.message));
    } else if (page === "settings") {
      api("/api/settings").then(d => setSettings(d.settings || {})).catch(e => setMessage(e.message));
    } else if (page === "analytics") {
      api("/api/analytics").then(d => setAnalytics(d.analytics || {})).catch(e => setMessage(e.message));
    } else if (page === "premium") {
      api("/api/premium/status").then(setPremium).catch(e => setMessage(e.message));
    } else if (page === "jobs") {
      loadJobs("");
    }
  }, [page, currentUser]);

  async function loadJobs(search) {
    if (!currentUser) return onNavigate("login");
    setBusy(true);
    setMessage("");
    try {
      const d = await api(`/api/jobs?search=${encodeURIComponent(search)}`);
      setJobs(d.jobs || []);
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function startMock() {
    if (!currentUser) return onNavigate("login");
    setBusy(true);
    setMessage("");
    setMockAnswer("");
    setMockEvaluation(null);
    setMockFinal(null);
    setMockHistory([]);
    try {
      const d = await api("/api/mock/start", { method: "POST", body: JSON.stringify({ role: mockRole }) });
      setMockSession({ id: d.session_id, question: d.question, role: d.role, question_number: d.question_number || 1, total_questions: d.total_questions || 10 });
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitMock() {
    if (!mockSession || !mockAnswer.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const d = await api(`/api/mock/${mockSession.id}/answer`, { method: "POST", body: JSON.stringify({ answer: mockAnswer.trim() }) });
      setMockEvaluation(d.evaluation || null);
      setMockHistory(prev => [...prev, { question: mockSession.question, answer: mockAnswer.trim(), ...(d.evaluation || {}) }]);
      setMockAnswer("");

      if (d.completed || d.final_result) {
        setMockFinal(d.final_result || d);
        setMockSession(null);
      } else {
        setMockSession(prev => ({ ...prev, question: d.next_question, question_number: d.question_number || ((prev?.question_number || 1) + 1), total_questions: d.total_questions || 10 }));
      }
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveApplication(e) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const d = await api("/api/applications", { method: "POST", body: JSON.stringify(appForm) });
      setApplications(prev => [d.application, ...prev]);
      setAppForm({ company: "", role: "", location: "", url: "", status: "Applied", notes: "" });
      setMessage("Application saved successfully.");
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateApplication(id, status) {
    try {
      const d = await api(`/api/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setApplications(prev => prev.map(a => a.id === id ? d.application : a));
    } catch (e) {
      setMessage(e.message);
    }
  }

  async function deleteApplication(id) {
    try {
      await api(`/api/applications/${id}`, { method: "DELETE" });
      setApplications(prev => prev.filter(a => a.id !== id));
    } catch (e) {
      setMessage(e.message);
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api("/api/profile", { method: "PUT", body: JSON.stringify(profile) });
      const updatedUser = { ...currentUser, name: profile.name };
      localStorage.setItem("resumeai_user", JSON.stringify(updatedUser));
      setMessage("Profile saved successfully.");
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveSettings(e) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api("/api/settings", { method: "PUT", body: JSON.stringify(settings) });
      setMessage("Settings saved successfully.");
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!currentUser) {
    return <SimplePage title="Login required" icon="🔐" description="Sign in to use this workspace feature."><div className="workspace-module"><p>Please log in first so your data can be saved to your account.</p><button className="workspace-primary" onClick={() => onNavigate("login")}>Login →</button></div></SimplePage>;
  }

  if (page === "mocks") {
    const currentNumber = mockSession?.question_number || (mockFinal ? 10 : 0);
    const progress = mockSession ? Math.max(0, Math.min(100, ((currentNumber - 1) / 10) * 100)) : (mockFinal ? 100 : 0);
    return (
      <main className="workspace-page mock-pro-shell">
        <div className="workspace-welcome mock-hero-card">
          <div><span className="workspace-eyebrow">AI CAREER PRACTICE</span><h1>Mock Interview</h1><p>Practice with role-specific questions and receive objective feedback after every answer.</p></div>
          <span className="mock-hero-badge">🤖 AI Powered</span>
        </div>
        {!mockSession && !mockFinal && (
          <section className="mock-interview-card mock-start-card">
            <div className="mock-start-icon">🎤</div>
            <span className="workspace-eyebrow">READY WHEN YOU ARE</span>
            <h2>Choose your target role</h2>
            <p>The interview contains exactly 10 questions. Later questions adapt to your previous answers when AI evaluation is available.</p>
            <div className="mock-role-row"><label>Target role</label><input value={mockRole} onChange={e => setMockRole(e.target.value)} placeholder="e.g. Software Engineer" /><button className="workspace-primary" onClick={startMock} disabled={busy}>{busy ? "Starting..." : "Start Interview →"}</button></div>
          </section>
        )}
        {mockSession && (
          <section className="mock-interview-card">
            <div className="mock-progress-head"><span>QUESTION {currentNumber} OF 10</span><strong>{Math.round(progress)}%</strong></div>
            <div className="mock-progress"><span style={{ width: `${progress}%` }} /></div>
            <div className="mock-question-box"><span>🤖</span><div><small>AI Interviewer · {mockSession.role}</small><h2>{mockSession.question}</h2></div></div>
            <label className="mock-answer-label">Your answer</label>
            <textarea rows="8" value={mockAnswer} onChange={e => setMockAnswer(e.target.value)} placeholder="Type your answer here. Be specific and answer the question directly..." />
            <div className="mock-submit-row"><span>{mockAnswer.trim().length} characters</span><button className="workspace-primary" onClick={submitMock} disabled={busy || !mockAnswer.trim()}>{busy ? "Evaluating..." : currentNumber === 10 ? "Submit & Finish" : "Submit Answer →"}</button></div>
            {mockEvaluation && <div className="mock-evaluation"><div className="mock-score-pill">{mockEvaluation.score ?? "—"}<small>/10</small></div><div><b>{mockEvaluation.verdict || "AI feedback"}</b><p>{mockEvaluation.feedback || "Feedback unavailable."}</p>{mockEvaluation.correctness && <span>{mockEvaluation.correctness}</span>}</div></div>}
          </section>
        )}
        {mockFinal && (
          <section className="mock-final-card"><div className="mock-final-icon">🏆</div><span className="workspace-eyebrow">INTERVIEW COMPLETE</span><h2>Your final result</h2><div className="mock-final-score">{mockFinal.score ?? mockFinal.final_score ?? 0}<small>/100</small></div><div className="mock-final-grid"><div><b>{mockHistory.length}</b><span>Questions completed</span></div><div><b>{mockHistory.filter(x => Number(x.score) >= 7).length}</b><span>Strong answers</span></div><div><b>{mockHistory.length ? (mockHistory.reduce((s,x) => s + Number(x.score || 0),0) / mockHistory.length).toFixed(1) : "0.0"}</b><span>Average /10</span></div></div><p>{mockFinal.feedback || mockFinal.overall_feedback || "Review each answer and use the feedback to improve your next interview."}</p><button className="workspace-primary" onClick={startMock}>Practice Again →</button></section>
        )}
        {message && <div className="workspace-alert">⚠️ {message}</div>}
      </main>
    );
  }

  if (page === "jobs") {
    return (
      <main className="workspace-page jobs-page">
        <div className="workspace-welcome"><div><span className="workspace-eyebrow">CAREER OPPORTUNITIES</span><h1>Find your next opportunity</h1><p>Search live remote listings and open the original posting to apply.</p></div><span className="jobs-hero-icon">💼</span></div>
        <section className="jobs-search-card"><form onSubmit={e => { e.preventDefault(); loadJobs(jobSearch); }}><div className="jobs-search-input"><span>⌕</span><input value={jobSearch} onChange={e => setJobSearch(e.target.value)} placeholder="Search jobs, e.g. React, Python, Data Analyst" /></div><button className="workspace-primary" disabled={busy}>{busy ? "Searching..." : "Search Jobs"}</button></form></section>
        {message && <div className="workspace-alert">⚠️ {message}</div>}
        <section className="jobs-grid">{jobs.map(job => <article className="job-card-modern" key={job.id}><div className="job-card-top"><span className="job-company-icon">{String(job.company || "J").slice(0,1).toUpperCase()}</span><span className="job-source">LIVE LISTING</span></div><h3>{job.title}</h3><p className="job-company">{job.company}</p><p className="job-location">📍 {job.location || "Remote"}</p><div className="job-card-footer"><span>🌐 Remotive</span><a href={job.url} target="_blank" rel="noreferrer">View job ↗</a></div></article>)}</section>
        {!jobs.length && !busy && <div className="workspace-empty"><div className="workspace-empty-icon">💼</div><h2>No job listings yet</h2><p>Search for a role to load available listings.</p></div>}
        <small className="jobs-source-note">Source: Remotive. Job data may be delayed by the source.</small>
      </main>
    );
  }

  if (page === "applications") {
    return (
      <main className="workspace-page applications-page">
        <div className="workspace-welcome"><div><span className="workspace-eyebrow">JOB TRACKER</span><h1>My Applications</h1><p>Keep every application organized from one professional workspace.</p></div><span className="applications-count">📋 {applications.length} tracked</span></div>
        <div className="applications-layout"><section className="application-form-card"><div className="section-heading-row"><div><h2>Add application</h2><p>Save a role as soon as you apply.</p></div><span>➕</span></div><form onSubmit={saveApplication} className="application-form"><label>Company<input placeholder="Company name" value={appForm.company} onChange={e => setAppForm({...appForm,company:e.target.value})} required /></label><label>Role<input placeholder="Job title" value={appForm.role} onChange={e => setAppForm({...appForm,role:e.target.value})} required /></label><label>Location<input placeholder="Remote / City" value={appForm.location} onChange={e => setAppForm({...appForm,location:e.target.value})} /></label><label>Job URL<input placeholder="https://..." value={appForm.url} onChange={e => setAppForm({...appForm,url:e.target.value})} /></label><label>Status<select value={appForm.status} onChange={e => setAppForm({...appForm,status:e.target.value})}><option>Applied</option><option>Interview</option><option>Offer</option><option>Rejected</option><option>Withdrawn</option></select></label><label className="application-notes">Notes<textarea placeholder="Add a note..." value={appForm.notes} onChange={e => setAppForm({...appForm,notes:e.target.value})} /></label><button className="workspace-primary" disabled={busy}>{busy ? "Saving..." : "Save Application"}</button></form>{message && <p className="workspace-message">{message}</p>}</section><section className="applications-list-card"><div className="section-heading-row"><div><h2>Application history</h2><p>Your saved applications and current status.</p></div></div><div className="application-list">{applications.map(a => <article className="application-card-modern" key={a.id}><div className="application-company-icon">{String(a.company || "C").slice(0,1).toUpperCase()}</div><div className="application-main"><h3>{a.role}</h3><p>{a.company} · {a.location || "Location not specified"}</p><div className="application-meta">Applied {a.applied_at ? new Date(a.applied_at).toLocaleDateString() : "recently"}</div></div><div className="application-actions"><select value={a.status} onChange={e => updateApplication(a.id,e.target.value)}><option>Applied</option><option>Interview</option><option>Offer</option><option>Rejected</option><option>Withdrawn</option></select>{a.url && <a href={a.url} target="_blank" rel="noreferrer">Open ↗</a>}<button className="danger-ghost" onClick={() => deleteApplication(a.id)}>Delete</button></div></article>)}</div>{!applications.length && <div className="workspace-empty"><div className="workspace-empty-icon">📋</div><h2>No applications yet</h2><p>Add your first application to start tracking your job search.</p></div>}</section></div>
      </main>
    );
  }

  if (page === "profile") {
    const skillList = String(profile.skills || "").split(",").map(s => s.trim()).filter(Boolean);
    const strength = Math.round(([profile.name, profile.email, profile.phone, profile.location, profile.headline, profile.bio, profile.skills].filter(Boolean).length / 7) * 100);
    return <SimplePage title="Profile" icon="👤" description="Build the professional profile ResumeAI can use across your workspace."><div className="profile-pro-shell"><section className="profile-cover-card"><div className="profile-avatar">{(profile.name || "U").trim().charAt(0).toUpperCase()}</div><div className="profile-cover-info"><span className="workspace-eyebrow">YOUR PROFESSIONAL PROFILE</span><h2>{profile.name || "Your Name"}</h2><p>{profile.headline || "Add a professional headline to introduce yourself."}</p><div className="profile-meta-row"><span>✉️ {profile.email || "Email not added"}</span><span>📍 {profile.location || "Location not added"}</span></div></div><div className="profile-completion"><span>Profile strength</span><strong>{Math.min(100,strength)}%</strong></div></section><div className="profile-grid"><section className="workspace-module profile-form-card"><div className="mock-section-heading"><div><span>🪪</span><div><h3>Personal information</h3><p>Keep your professional details current.</p></div></div></div><form onSubmit={saveProfile}><label>Full name<input value={profile.name || ""} onChange={e=>setProfile({...profile,name:e.target.value})} required /></label><label>Email<input value={profile.email || ""} readOnly /></label><label>Phone<input value={profile.phone || ""} onChange={e=>setProfile({...profile,phone:e.target.value})} /></label><label>Location<input value={profile.location || ""} onChange={e=>setProfile({...profile,location:e.target.value})} /></label><label>Professional headline<input value={profile.headline || ""} onChange={e=>setProfile({...profile,headline:e.target.value})} placeholder="e.g. B.Tech student | Aspiring Software Engineer" /></label><label>About you<textarea rows="5" value={profile.bio || ""} onChange={e=>setProfile({...profile,bio:e.target.value})} /></label><label>Skills <span className="field-hint">Separate with commas</span><textarea rows="4" value={profile.skills || ""} onChange={e=>setProfile({...profile,skills:e.target.value})} placeholder="Python, React, SQL, FastAPI" /></label><button className="workspace-primary" disabled={busy}>{busy ? "Saving..." : "Save Profile"}</button></form>{message && <p className="workspace-message">{message}</p>}</section><aside className="profile-side-column"><section className="workspace-module profile-preview-card"><div className="mock-section-heading"><div><span>✨</span><div><h3>Profile preview</h3><p>How your professional identity looks.</p></div></div></div><div className="profile-preview-inner"><div className="profile-mini-avatar">{(profile.name || "U").trim().charAt(0).toUpperCase()}</div><h3>{profile.name || "Your Name"}</h3><p>{profile.headline || "Professional headline"}</p><div className="profile-skill-list">{(skillList.length ? skillList : ["Add skills"]).slice(0,8).map((s,i)=><span key={i}>{s}</span>)}</div></div></section><section className="profile-tip-card"><span>💡</span><div><b>Profile tip</b><p>Use a clear headline and only list skills you can genuinely discuss.</p></div></section></aside></div></div></SimplePage>;
  }

  if (page === "settings") {
    return <SimplePage title="Settings" icon="⚙️" description="Control your ResumeAI workspace preferences."><div className="settings-pro-shell"><section className="settings-header-card"><div className="settings-header-icon">⚙️</div><div><span className="workspace-eyebrow">WORKSPACE PREFERENCES</span><h2>Make ResumeAI work your way</h2><p>Choose how notifications and language preferences behave across your account.</p></div></section><form className="settings-list-card" onSubmit={saveSettings}><div className="settings-row"><div className="settings-row-icon">🔔</div><div className="settings-row-copy"><b>Email notifications</b><span>Receive important account and workspace updates.</span></div><label className="toggle"><input type="checkbox" checked={Boolean(settings.email_notifications)} onChange={e=>setSettings({...settings,email_notifications:e.target.checked})}/><span /></label></div><div className="settings-row"><div className="settings-row-icon">📈</div><div className="settings-row-copy"><b>Weekly career summary</b><span>Keep a weekly view of your ResumeAI activity.</span></div><label className="toggle"><input type="checkbox" checked={Boolean(settings.weekly_summary)} onChange={e=>setSettings({...settings,weekly_summary:e.target.checked})}/><span /></label></div><div className="settings-row"><div className="settings-row-icon">🌐</div><div className="settings-row-copy"><b>Workspace language</b><span>Choose your preferred interface language.</span></div><select value={settings.language || "English"} onChange={e=>setSettings({...settings,language:e.target.value})}><option>English</option><option>Hindi</option><option>Hinglish</option></select></div><div className="settings-save-bar"><div><b>Preferences</b><span>Your changes are saved to your account.</span></div><button className="workspace-primary" disabled={busy}>{busy ? "Saving..." : "Save Changes"}</button></div>{message && <p className="workspace-message">{message}</p>}</form><section className="settings-info-grid"><div><span>🔒</span><b>Account privacy</b><p>Your workspace settings are tied to your account.</p></div><div><span>🧠</span><b>AI language</b><p>AI Career Chat can respond in English, Hindi or Hinglish based on your question.</p></div><div><span>✨</span><b>ResumeAI experience</b><p>Preferences do not change the truthfulness of analysis results.</p></div></section></div></SimplePage>;
  }

  if (page === "analytics") return <SimplePage title="Analytics" icon="📊" description="Your saved workspace activity, not invented numbers."><div className="workspace-stats"><div className="workspace-stat"><span>📄</span><div><small>Resumes analyzed</small><strong>{analytics?.resumes ?? "—"}</strong></div></div><div className="workspace-stat"><span>🎯</span><div><small>Average resume score</small><strong>{analytics?.average_resume_score != null ? `${analytics.average_resume_score}/100` : "—"}</strong></div></div><div className="workspace-stat"><span>📋</span><div><small>Applications</small><strong>{analytics?.applications ?? "—"}</strong></div></div><div className="workspace-stat"><span>🎤</span><div><small>Mock interviews</small><strong>{analytics?.mock_interviews ?? "—"}</strong></div></div></div></SimplePage>;

  if (page === "premium") return <SimplePage title="Premium" icon="⭐" description="Premium is available only after a real payment gateway is configured."><div className="workspace-module"><h2>⭐ ResumeAI Premium</h2><p>{premium?.message || "Payment setup is not active yet."}</p></div></SimplePage>;

  return null;
}

function SimplePage({ title, icon, description, children }) {
  return (
    <main className="workspace-page">
      <div className="workspace-welcome">
        <div>
          <span className="workspace-eyebrow">RESUMEAI</span>
          <h1>{icon} {title}</h1>
          <p>{description}</p>
        </div>
      </div>
      <section className="workspace-card workspace-full-card">{children}</section>
    </main>
  );
}

function App() {
  const [activePage, setActivePage] = useState("resume");
  const [accountOpen, setAccountOpen] = useState(false);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("resumeai_user")) || null;
    } catch {
      return null;
    }
  });
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [authMessageType, setAuthMessageType] = useState("");

  const [dashboardStats, setDashboardStats] = useState({
    total_resumes: 0,
    latest_score: null,
    mock_interviews: 0,
    applications: 0,
    average_mock_score: null,
  });

  const [file, setFile] = useState(null);

  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] =
    useState("");

  const [result, setResult] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [aiAdvice, setAiAdvice] = useState(null);
  const [aiStatus, setAiStatus] = useState("");

  const [chatMessages, setChatMessages] =
    useState([]);

  const [chatInput, setChatInput] =
    useState("");

  const [chatLoading, setChatLoading] =
    useState(false);

  const [enhancing, setEnhancing] =
    useState(false);

  const [checkingPhoto, setCheckingPhoto] =
    useState(false);

  const [
    showEnhancePhotoOptions,
    setShowEnhancePhotoOptions,
  ] = useState(false);

  const [
    originalPhotoDetected,
    setOriginalPhotoDetected,
  ] = useState(null);

  const [enhancedResume, setEnhancedResume] =
    useState("");

  const [enhancedPdf, setEnhancedPdf] =
    useState("");

  const [
    enhancedFilename,
    setEnhancedFilename,
  ] = useState("");

  const [enhanceError, setEnhanceError] =
    useState("");

  const [
    showScoreDetails,
    setShowScoreDetails,
  ] = useState(false);

  const resumeJobId =
    result?.resume_job_id ||
    result?.job_id ||
    result?.ai_feedback_job_id;

  const score = Number(
    result?.score || 0
  );

  const scoreInfo =
    getScoreInfo(score);

  const detectedSections =
    canonicalSections(
      result?.detected_sections ||
        result?.sections ||
        []
    );

  const skills = Array.isArray(
    result?.skills
  )
    ? result.skills
    : Array.isArray(
        result?.skills_detected
      )
      ? result.skills_detected
      : [];

  const strengths = Array.isArray(
    result?.strengths
  )
    ? result.strengths
    : [];

  const suggestions = Array.isArray(
    result?.suggestions
  )
    ? result.suggestions
    : [];

  const actionPlan =
    Array.isArray(
      result?.action_plan
    ) &&
    result.action_plan.length > 0
      ? result.action_plan
      : suggestions;

  const breakdown =
    result?.breakdown || {};

  useEffect(() => {
    if (!currentUser) return;
    const token = localStorage.getItem("resumeai_token");
    if (!token) return;

    fetch(`${API_URL}/api/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (response.status === 401) {
          localStorage.removeItem("resumeai_token");
          localStorage.removeItem("resumeai_user");
          setCurrentUser(null);
          setAuthMessage("Please log in again to this backend.");
          setAuthMessageType("error");
          return null;
        }
        if (!response.ok) throw new Error(data.detail || "Could not load dashboard.");
        return data;
      })
      .then((data) => {
        if (data?.dashboard) setDashboardStats(data.dashboard);
      })
      .catch((err) => console.error("Dashboard load failed:", err));
  }, [currentUser]);

  function handleFileChange(event) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) return;

    setFile(selectedFile);

    setPhoto(null);
    setPhotoPreview("");

    setResult(null);
    setError("");

    setAiAdvice(null);
    setAiStatus("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setEnhanceError("");

    setShowEnhancePhotoOptions(false);
    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setShowScoreDetails(false);

    setChatMessages([]);
    setChatInput("");
  }

  function handlePhotoChange(event) {
    const selectedPhoto =
      event.target.files?.[0];

    if (!selectedPhoto) return;

    if (
      ![
        "image/jpeg",
        "image/png",
      ].includes(selectedPhoto.type)
    ) {
      setEnhanceError(
        "Please select a JPG or PNG photo."
      );
      return;
    }

    setPhoto(selectedPhoto);
    setEnhanceError("");

    const url =
      URL.createObjectURL(
        selectedPhoto
      );

    setPhotoPreview(url);
  }

  async function fetchAIAdvice(jobId) {
    setAiStatus("processing");

    for (let i = 0; i < 80; i += 1) {
      try {
        const response =
          await fetch(
            `${API_URL}/ai-feedback/${jobId}`
          );

        const data =
          await response.json();

        if (
          data.status ===
          "completed"
        ) {
          setAiAdvice(
            data.ai_feedback
          );

          setAiStatus(
            "completed"
          );

          return;
        }

        if (
          data.status === "failed"
        ) {
          setAiStatus("failed");
          return;
        }
      } catch {
        // Keep polling.
      }

      await new Promise(
        (resolve) =>
          setTimeout(
            resolve,
            1500
          )
      );
    }

    setAiStatus("failed");
  }

  async function analyzeResume() {
    if (!file) {
      setError(
        "Please select a resume first."
      );
      return;
    }

    setLoading(true);
    setError("");

    setResult(null);
    setAiAdvice(null);
    setAiStatus("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setEnhanceError("");

    setShowEnhancePhotoOptions(
      false
    );

    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setPhoto(null);
    setPhotoPreview("");

    setShowScoreDetails(false);

    setChatMessages([]);
    setChatInput("");

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const response =
        await fetch(
          `${API_URL}/analyze`,
          {
            method: "POST",
            headers: (() => {
              const token = localStorage.getItem("resumeai_token");
              return token ? { Authorization: `Bearer ${token}` } : {};
            })(),
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.message ||
            "Resume analysis failed."
        );
      }

      setResult(data);

      const dashboardToken = localStorage.getItem("resumeai_token");
      if (dashboardToken) {
        fetch(`${API_URL}/api/dashboard`, {
          headers: { Authorization: `Bearer ${dashboardToken}` },
        })
          .then((r) => r.ok ? r.json() : null)
          .then((d) => {
            if (d?.dashboard) setDashboardStats(d.dashboard);
          })
          .catch(() => {});
      }

      const jobId =
        data.resume_job_id ||
        data.ai_feedback_job_id ||
        data.job_id;

      if (jobId) {
        fetchAIAdvice(jobId);
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not analyze the resume."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleEnhanceClick() {
    if (!resumeJobId) {
      setEnhanceError(
        "Please analyze a resume first."
      );
      return;
    }

    if (!file) {
      setEnhanceError(
        "Original resume file is not available."
      );
      return;
    }

    setCheckingPhoto(true);
    setEnhanceError("");
    setShowEnhancePhotoOptions(false);

    try {
      const formData =
        new FormData();

      formData.append(
        "job_id",
        resumeJobId
      );

      formData.append(
        "resume_file",
        file
      );

      const response =
        await fetch(
          `${API_URL}/enhance-photo-status`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        data.success === false
      ) {
        throw new Error(
          data.message ||
            "Could not check the original resume photo."
        );
      }

      const detected =
        Boolean(
          data.photo_detected
        );

      setOriginalPhotoDetected(
        detected
      );

      if (detected) {
        await createEnhancedResume(
          null
        );
      } else {
        setShowEnhancePhotoOptions(
          true
        );
      }
    } catch (err) {
      setEnhanceError(
        err.message ||
          "Could not check the resume photo."
      );
    } finally {
      setCheckingPhoto(false);
    }
  }

  async function createEnhancedResume(
    photoToSend = null
  ) {
    if (!resumeJobId) {
      setEnhanceError(
        "Please analyze a resume first."
      );
      return;
    }

    if (!file) {
      setEnhanceError(
        "Original resume file is not available."
      );
      return;
    }

    setEnhancing(true);
    setEnhanceError("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");

    try {
      const formData =
        new FormData();

      formData.append(
        "job_id",
        resumeJobId
      );

      formData.append(
        "resume_file",
        file
      );

      if (photoToSend) {
        formData.append(
          "photo",
          photoToSend
        );
      }

      const response =
        await fetch(
          `${API_URL}/enhance`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.message ||
            "Resume enhancement failed."
        );
      }

      setEnhancedResume(
        data.enhanced_resume || ""
      );

      setEnhancedPdf(
        data.pdf_base64 || ""
      );

      setEnhancedFilename(
        data.filename ||
          "ResumeAI-Professional-Resume.pdf"
      );

      setShowEnhancePhotoOptions(
        false
      );
    } catch (err) {
      setEnhanceError(
        err.message ||
          "Could not create the professional resume."
      );
    } finally {
      setEnhancing(false);
    }
  }

  async function skipPhotoAndEnhance() {
    setPhoto(null);
    setPhotoPreview("");
    setEnhanceError("");

    await createEnhancedResume(
      null
    );
  }

  async function addPhotoAndEnhance() {
    if (!photo) {
      setEnhanceError(
        "Please choose a JPG or PNG photo first."
      );
      return;
    }

    await createEnhancedResume(
      photo
    );
  }

  function downloadEnhancedPDF() {
    if (!enhancedPdf) {
      setEnhanceError(
        "The PDF is not ready yet."
      );
      return;
    }

    try {
      const binary =
        atob(enhancedPdf);

      const bytes =
        new Uint8Array(
          binary.length
        );

      for (
        let i = 0;
        i < binary.length;
        i += 1
      ) {
        bytes[i] =
          binary.charCodeAt(i);
      }

      const blob =
        new Blob(
          [bytes],
          {
            type: "application/pdf",
          }
        );

      const url =
        URL.createObjectURL(
          blob
        );

      const link =
        document.createElement(
          "a"
        );

      link.href = url;

      link.download =
        enhancedFilename ||
        "ResumeAI-Professional-Resume.pdf";

      document.body.appendChild(
        link
      );

      link.click();

      link.remove();

      URL.revokeObjectURL(url);
    } catch {
      setEnhanceError(
        "Could not download the PDF."
      );
    }
  }

  async function sendChatMessage() {
    const message =
      chatInput.trim();

    if (
      !message ||
      !resumeJobId
    ) {
      return;
    }

    setChatInput("");

    setChatMessages(
      (previous) => [
        ...previous,
        {
          role: "user",
          text: message,
        },
      ]
    );

    setChatLoading(true);

    try {
      const response =
        await fetch(
          `${API_URL}/chat`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              job_id:
                resumeJobId,
              message,
            }),
          }
        );

      const data =
        await response.json();

      if (!data.success) {
        throw new Error(
          data.message ||
            "Chat request failed."
        );
      }

      const chatJobId =
        data.chat_job_id;

      if (!chatJobId) {
        throw new Error(
          "AI chat job was not created."
        );
      }

      for (
        let i = 0;
        i < 80;
        i += 1
      ) {
        const pollResponse =
          await fetch(
            `${API_URL}/chat/${chatJobId}`
          );

        const pollData =
          await pollResponse.json();

        if (
          pollData.status ===
          "completed"
        ) {
          setChatMessages(
            (previous) => [
              ...previous,
              {
                role: "assistant",
                text:
                  pollData.chat_answer ||
                  pollData.answer ||
                  "",
              },
            ]
          );

          break;
        }

        if (
          pollData.status ===
          "failed"
        ) {
          throw new Error(
            pollData.message ||
              "AI chat failed."
          );
        }

        await new Promise(
          (resolve) =>
            setTimeout(
              resolve,
              1200
            )
        );
      }
    } catch (err) {
      setChatMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text:
              err.message ||
              "Sorry, AI chat failed.",
          },
        ]
      );
    } finally {
      setChatLoading(false);
    }
  }

  function handleChatKeyDown(
    event
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendChatMessage();
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage("");
    setAuthMessageType("");

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail.trim(),
          password: loginPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      localStorage.setItem("resumeai_token", data.access_token);
      localStorage.setItem("resumeai_user", JSON.stringify(data.user));

      setCurrentUser(data.user);
      setLoginEmail("");
      setLoginPassword("");
      setAuthMessage("Login successful!");
      setAuthMessageType("success");
      setAccountOpen(false);

      setTimeout(() => {
        setAuthMessage("");
        setAuthMessageType("");
        setActivePage("dashboard");
      }, 500);
    } catch (err) {
      setAuthMessage(err.message || "Unable to login.");
      setAuthMessageType("error");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSignup(e) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage("");
    setAuthMessageType("");

    try {
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: signupName.trim(),
          email: signupEmail.trim(),
          password: signupPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Account creation failed.");
      }

      localStorage.setItem("resumeai_token", data.access_token);
      localStorage.setItem("resumeai_user", JSON.stringify(data.user));

      setCurrentUser(data.user);
      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setAuthMessage("Account created successfully!");
      setAuthMessageType("success");
      setAccountOpen(false);

      setTimeout(() => {
        setAuthMessage("");
        setAuthMessageType("");
        setActivePage("dashboard");
      }, 500);
    } catch (err) {
      setAuthMessage(err.message || "Unable to create account.");
      setAuthMessageType("error");
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("resumeai_token");
    localStorage.removeItem("resumeai_user");
    setCurrentUser(null);
    setAccountOpen(false);
    setActivePage("dashboard");
  }

  function resetApp() {
    setActivePage("resume");
    setFile(null);

    setPhoto(null);
    setPhotoPreview("");

    setResult(null);
    setError("");

    setAiAdvice(null);
    setAiStatus("");

    setChatMessages([]);
    setChatInput("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setEnhanceError("");

    setShowEnhancePhotoOptions(
      false
    );

    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setShowScoreDetails(false);
  }

  function DashboardHome() {
    const analyzed = Boolean(result);
    return (
      <main className="workspace-page">
        <div className="workspace-welcome">
          <div><span className="workspace-eyebrow">RESUMEAI DASHBOARD</span><h1>Welcome back! 👋</h1><p>Your journey to a better career starts here.</p></div>
          <button className="workspace-primary" onClick={() => setActivePage("resume")}>{analyzed ? "Analyze New Resume →" : "Analyze Resume →"}</button>
        </div>
        <div className="workspace-stats">
          <div className="workspace-stat"><span>📄</span><div><small>Total Resumes</small><strong>{dashboardStats.total_resumes}</strong><em>{dashboardStats.total_resumes ? `${dashboardStats.total_resumes} analyzed` : "No resume yet"}</em></div></div>
          <div className="workspace-stat"><span>🎯</span><div><small>Latest Score</small><strong>{dashboardStats.latest_score != null ? `${dashboardStats.latest_score}%` : "—"}</strong><em>{dashboardStats.latest_score != null ? getScoreInfo(dashboardStats.latest_score).label : "Analyze a resume first"}</em></div></div>
          <div className="workspace-stat"><span>💼</span><div><small>Applications</small><strong>{dashboardStats.applications}</strong><em>{dashboardStats.applications ? "Tracked applications" : "No applications yet"}</em></div></div>
          <div className="workspace-stat"><span>🎤</span><div><small>Mock Interviews</small><strong>{dashboardStats.mock_interviews}</strong><em>{dashboardStats.mock_interviews ? "Sessions completed" : "No interviews yet"}</em></div></div>
        </div>
        <div className="workspace-columns">
          <section className="workspace-card workspace-score-card">
            <div className="workspace-card-title"><span>Resume Analysis</span><button onClick={() => setActivePage("resume")}>Open Analyzer</button></div>
            {analyzed ? <div className="workspace-score-body"><div className={`workspace-score-ring ${scoreInfo.className}`}><strong>{score}</strong><span>ATS score</span></div><div><h2>{scoreInfo.label}</h2><p>{result.verdict_message || scoreInfo.message}</p><button className="workspace-primary" onClick={() => setActivePage("resume")}>View Full Report →</button></div></div> : <div className="workspace-empty"><div className="workspace-empty-icon">📄</div><h2>No resume analyzed yet</h2><p>Upload a resume to get your score, AI feedback and improvement plan.</p><button className="workspace-primary" onClick={() => setActivePage("resume")}>Upload Resume →</button></div>}
          </section>
          <section className="workspace-card"><div className="workspace-card-title"><span>Quick Actions</span></div><div className="workspace-actions"><button onClick={() => setActivePage("resume")}>⬆️ <span>Analyze Resume</span> →</button><button onClick={() => setActivePage("mocks")}>🎤 <span>Take Mock Interview</span> →</button><button onClick={() => setActivePage("jobs")}>💼 <span>Browse Jobs</span> →</button><button onClick={() => setActivePage("applications")}>📋 <span>My Applications</span> →</button></div></section>
        </div>
        <div className="workspace-columns workspace-bottom">
          <section className="workspace-card"><div className="workspace-card-title"><span>Recent Activity</span></div>{analyzed ? <div className="workspace-activity"><div>📄 <span>Resume analyzed</span><small>Score: {score}%</small></div><div>🤖 <span>AI feedback</span><small>{aiStatus || "Available"}</small></div><div>✨ <span>Enhancement</span><small>Available in Analyzer</small></div></div> : <p className="workspace-muted">Your real activity will appear here after you use ResumeAI.</p>}</section>
          <section className="workspace-card"><div className="workspace-card-title"><span>Resume Tips</span></div><div className="workspace-tips"><div><b>1</b><span>Use measurable achievements when your resume supports them.</span></div><div><b>2</b><span>Keep section headings clear and consistent.</span></div><div><b>3</b><span>Use relevant skills without inventing experience.</span></div><div><b>4</b><span>Keep the format clean and ATS-friendly.</span></div></div></section>
        </div>
        <section className="workspace-ai-banner"><div><span>🤖</span><div><h2>Let AI Build Your Future</h2><p>Get evidence-based resume feedback and career guidance.</p></div></div><button onClick={() => setActivePage("resume")}>Try ResumeAI →</button></section>
      </main>
    );
  }

  return (
    <div className="app-shell workspace-shell">
      <header className="workspace-topbar">
        <button className="workspace-brand" onClick={() => setActivePage("dashboard")}><span className="workspace-brand-logo">R</span><span><b>Resume<span>AI</span></b><small>Career Intelligence</small></span></button>
        <nav className="workspace-topnav"><button className={activePage === "dashboard" ? "active" : ""} onClick={() => setActivePage("dashboard")}>⌂ Dashboard</button><button className={activePage === "mocks" ? "active" : ""} onClick={() => setActivePage("mocks")}>▣ Mocks</button><button className={activePage === "jobs" ? "active" : ""} onClick={() => setActivePage("jobs")}>▣ Jobs</button><button className={activePage === "resources" ? "active" : ""} onClick={() => setActivePage("resources")}>▤ Resources</button><button className={activePage === "analytics" ? "active" : ""} onClick={() => setActivePage("analytics")}>⌁ Analytics</button></nav>
        <div className="workspace-account-wrap">
          <button className="workspace-account" onClick={() => setAccountOpen(!accountOpen)}>
            <span className="workspace-avatar">👤</span>
            <span>{currentUser ? currentUser.name : "Login / Sign Up"}</span>
            <span>⌄</span>
          </button>
          {accountOpen && (
            <div className="workspace-account-menu">
              {currentUser ? (
                <>
                  <button onClick={() => { setAccountOpen(false); setActivePage("profile"); }}>👤 My Profile</button>
                  <button onClick={handleLogout}>⇥ Logout</button>
                </>
              ) : (
                <>
                  <button onClick={() => { setAccountOpen(false); setAuthMessage(""); setActivePage("login"); }}>⇥ Login</button>
                  <button onClick={() => { setAccountOpen(false); setAuthMessage(""); setActivePage("signup"); }}>＋ Create Account</button>
                </>
              )}
            </div>
          )}
        </div>
      </header>
      <aside className="workspace-sidebar"><div className="workspace-side-label">WORKSPACE</div><button className={activePage === "dashboard" ? "active" : ""} onClick={() => setActivePage("dashboard")}>⌂ <span>Dashboard</span></button><button className={activePage === "resume" ? "active" : ""} onClick={() => setActivePage("resume")}>▣ <span>Resume Analyzer</span></button><button className={activePage === "mocks" ? "active" : ""} onClick={() => setActivePage("mocks")}>◉ <span>Mocks</span></button><button className={activePage === "jobs" ? "active" : ""} onClick={() => setActivePage("jobs")}>▣ <span>Jobs</span></button><button className={activePage === "applications" ? "active" : ""} onClick={() => setActivePage("applications")}>➤ <span>My Applications</span></button><button className={activePage === "profile" ? "active" : ""} onClick={() => setActivePage("profile")}>◯ <span>Profile</span></button><button className={activePage === "settings" ? "active" : ""} onClick={() => setActivePage("settings")}>⚙ <span>Settings</span></button><div className="workspace-premium"><span>✦</span><h3>Upgrade to Premium</h3><p>Advanced AI tools and more career features.</p><button onClick={() => setActivePage("premium")}>Upgrade — ₹20</button></div><div className="workspace-side-footer"><b>ResumeAI</b><span>Build Better Resumes.<br/>Get Better Jobs.</span></div></aside>
      <div className="workspace-content">
        {activePage === "dashboard" && <DashboardHome />}
        {activePage === "mocks" && <WorkspaceModules page="mocks" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "jobs" && <WorkspaceModules page="jobs" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "applications" && <WorkspaceModules page="applications" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "resources" && <SimplePage title="Resources" icon="📚" description="Career resources from ResumeAI."><div className="workspace-module"><h2>Career Resources</h2><p>Resume writing, interview preparation and job-search guidance will be added here.</p></div></SimplePage>}
        {activePage === "analytics" && <WorkspaceModules page="analytics" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "profile" && <WorkspaceModules page="profile" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "settings" && <WorkspaceModules page="settings" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "login" && (
          <SimplePage title="Login" icon="🔐" description="Sign in to your ResumeAI account.">
            <form className="workspace-auth" onSubmit={handleLogin}>
              <h2>Login</h2>
              <input
                placeholder="Email"
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
              <input
                placeholder="Password"
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
              {authMessage && (
                <p style={{ color: authMessageType === "error" ? "#dc2626" : "#15803d", fontWeight: 600 }}>
                  {authMessage}
                </p>
              )}
              <button className="workspace-primary" type="submit" disabled={authLoading}>
                {authLoading ? "Logging in..." : "Login"}
              </button>
              <p>
                Don't have an account? {" "}
                <button type="button" onClick={() => { setAuthMessage(""); setActivePage("signup"); }}>
                  Create Account
                </button>
              </p>
            </form>
          </SimplePage>
        )}
        {activePage === "signup" && (
          <SimplePage title="Create Account" icon="✨" description="Create your ResumeAI account.">
            <form className="workspace-auth" onSubmit={handleSignup}>
              <h2>Create Account</h2>
              <input
                placeholder="Name"
                value={signupName}
                onChange={(e) => setSignupName(e.target.value)}
                required
              />
              <input
                placeholder="Email"
                type="email"
                value={signupEmail}
                onChange={(e) => setSignupEmail(e.target.value)}
                required
              />
              <input
                placeholder="Password (minimum 6 characters)"
                type="password"
                value={signupPassword}
                onChange={(e) => setSignupPassword(e.target.value)}
                minLength={6}
                required
              />
              {authMessage && (
                <p style={{ color: authMessageType === "error" ? "#dc2626" : "#15803d", fontWeight: 600 }}>
                  {authMessage}
                </p>
              )}
              <button className="workspace-primary" type="submit" disabled={authLoading}>
                {authLoading ? "Creating Account..." : "Create Account"}
              </button>
              <p>
                Already have an account? {" "}
                <button type="button" onClick={() => { setAuthMessage(""); setActivePage("login"); }}>
                  Login
                </button>
              </p>
            </form>
          </SimplePage>
        )}
        {activePage === "premium" && <WorkspaceModules page="premium" currentUser={currentUser} onNavigate={setActivePage} />}
        {activePage === "resume" && <div className="workspace-resume-content">
      <header className="topbar">
        <div className="brand">
          <div className="brand-logo">
            R
          </div>

          <div>
            <div className="brand-name">
              ResumeAI
            </div>

            <div className="brand-subtitle">
              AI Resume Analyzer
            </div>
          </div>
        </div>

        {result && (
          <button
            className="reset-button"
            onClick={resetApp}
          >
            New Resume
          </button>
        )}
      </header>

      {!result && (
        <main className="hero-section">
          <div className="hero-content">
            <div className="hero-badge">
              AI-POWERED RESUME ANALYZER
            </div>

            <h1>
              Make Your Resume
              <br />
              <span>Job Ready.</span>
            </h1>

            <p>
              Upload your resume and get an
              honest AI-powered analysis,
              actionable improvements and
              career guidance.
            </p>
          </div>

          <div className="upload-card">
            <div className="upload-icon">
              ↑
            </div>

            <h2>
              Upload Your Resume
            </h2>

            <p>
              PDF, DOCX, JPG or PNG
            </p>

            <label className="upload-button">
              Choose Resume

              <input
                type="file"
                accept=".pdf,.docx,.jpg,.jpeg,.png"
                onChange={
                  handleFileChange
                }
                hidden
              />
            </label>

            {file && (
              <div className="selected-file">
                <strong>
                  Selected:
                </strong>{" "}
                {file.name}
              </div>
            )}

            <button
              className="analyze-button"
              onClick={
                analyzeResume
              }
              disabled={
                loading || !file
              }
            >
              {loading
                ? "Analyzing..."
                : "Analyze Resume →"}
            </button>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}
          </div>
        </main>
      )}

      {result && (
        <main className="dashboard">
          <div className="dashboard-header">
            <div>
              <div className="hero-badge">
                ANALYSIS COMPLETE
              </div>

              <h1>
                Your Resume Report
              </h1>

              <p>
                Honest analysis based on the
                content detected in your resume.
              </p>
            </div>
          </div>

          {/* SCORE + OVERVIEW */}

          <div className="dashboard-grid">
            <section className="score-card">
              <div className="card-heading">
                <span>🎯</span>
                Resume Score
              </div>

              <div
                className={`score-circle ${scoreInfo.className}`}
              >
                <strong>
                  {score}
                </strong>

                <span>
                  / 100
                </span>
              </div>

              <div
                style={{
                  fontSize:
                    "2.1rem",
                  marginTop:
                    "4px",
                }}
              >
                {scoreInfo.emoji}
              </div>

              <h2>
                {scoreInfo.label}
              </h2>

              <p>
                {result.verdict_message ||
                  scoreInfo.message}
              </p>

              <button
                type="button"
                className="details-button"
                onClick={() =>
                  setShowScoreDetails(
                    !showScoreDetails
                  )
                }
              >
                {showScoreDetails
                  ? "Hide Score Details ↑"
                  : "View Score Details ↓"}
              </button>

              {showScoreDetails && (
                <div className="why-score">
                  <h3>
                    Why this score?
                  </h3>

                  {Array.isArray(
                    result.why_score
                  ) &&
                  result.why_score.length >
                    0 ? (
                    <ul>
                      {result.why_score.map(
                        (
                          item,
                          index
                        ) => (
                          <li
                            key={
                              index
                            }
                          >
                            {item}
                          </li>
                        )
                      )}
                    </ul>
                  ) : (
                    <p className="muted">
                      Your score is calculated
                      from content quality,
                      resume structure,
                      evidence and ATS-related
                      factors.
                    </p>
                  )}
                </div>
              )}
            </section>

            <section className="overview-card">
              <div className="card-heading">
                <span>📋</span>
                Resume Overview
              </div>

              <div className="section-status-list">
                {SECTION_LIST.map(
                  ([key, label]) => {
                    const present =
                      detectedSections.includes(
                        key
                      );

                    return (
                      <div
                        className="section-status"
                        key={key}
                      >
                        <span>
                          {label}
                        </span>

                        <span
                          className={
                            present
                              ? "status-present"
                              : "status-missing"
                          }
                        >
                          {present
                            ? "✓ Present"
                            : "✕ Missing"}
                        </span>
                      </div>
                    );
                  }
                )}
              </div>
            </section>
          </div>

          {/* QUICK INSIGHTS */}

          <section className="report-card">
            <div className="card-heading">
              <span>💡</span>
              Quick Resume Insights
            </div>

            <div className="analysis-grid">
              <div className="analysis-box">
                <h3>
                  📄 Resume Length
                </h3>

                <p className="insight-value">
                  {result.word_count ||
                    0}{" "}
                  words
                </p>

                <p className="muted">
                  Resume content detected by
                  ResumeAI.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  🛠️ Technical Skills
                </h3>

                <p className="insight-value">
                  {skills.length}
                </p>

                <p className="muted">
                  Recognizable technical skills
                  detected.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  📌 Resume Sections
                </h3>

                <p className="insight-value">
                  {detectedSections.length}
                </p>

                <p className="muted">
                  Resume sections detected
                  successfully.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  📈 Measurable Evidence
                </h3>

                <p className="insight-value">
                  {Array.isArray(
                    result.metrics_found
                  )
                    ? result.metrics_found
                        .length
                    : 0}
                </p>

                <p className="muted">
                  Metrics and measurable evidence
                  found.
                </p>
              </div>
            </div>
          </section>

          {/* SCORE BREAKDOWN */}

          <section className="report-card">
            <div className="card-heading">
              <span>📊</span>
              Score Breakdown
            </div>

            <div className="breakdown-grid">
              {Object.entries(
                breakdown
              ).map(
                ([key, value]) => (
                  <div
                    className="breakdown-item"
                    key={key}
                  >
                    <div>
                      {key
                        .replace(
                          /_/g,
                          " "
                        )
                        .replace(
                          /\b\w/g,
                          (char) =>
                            char.toUpperCase()
                        )}
                    </div>

                    <strong>
                      {value}
                    </strong>
                  </div>
                )
              )}
            </div>
          </section>

          {/* CONTENT ANALYSIS */}

          <section className="report-card">
            <div className="card-heading">
              <span>✨</span>
              Content Analysis
            </div>

            <div className="analysis-grid">
              <div className="analysis-box">
                <h3>
                  ✅ Strengths
                </h3>

                {strengths.length >
                0 ? (
                  <ul>
                    {strengths.map(
                      (
                        item,
                        index
                      ) => (
                        <li
                          key={index}
                        >
                          {item}
                        </li>
                      )
                    )}
                  </ul>
                ) : (
                  <p className="muted">
                    No major strengths were
                    detected yet.
                  </p>
                )}
              </div>

              <div className="analysis-box">
                <h3>
                  ⚠️ Improvements
                </h3>

                {suggestions.length >
                0 ? (
                  <ul>
                    {suggestions.map(
                      (
                        item,
                        index
                      ) => (
                        <li
                          key={index}
                        >
                          {item}
                        </li>
                      )
                    )}
                  </ul>
                ) : (
                  <p className="muted">
                    No major improvements
                    detected.
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* SKILLS */}

          <section className="report-card">
            <div className="card-heading">
              <span>🛠️</span>
              Detected Skills
            </div>

            <div className="skills-list">
              {skills.length >
              0 ? (
                skills.map(
                  (
                    skill,
                    index
                  ) => (
                    <span
                      className="skill-chip"
                      key={index}
                    >
                      {skill}
                    </span>
                  )
                )
              ) : (
                <p className="muted">
                  No recognizable technical
                  skills were detected.
                </p>
              )}
            </div>
          </section>

          {/* AI ADVISOR */}

          <section className="report-card ai-advisor">
            <div className="card-heading">
              <span>🤖</span>
              AI Career Advisor
            </div>

            <p className="muted">
              Personalized AI feedback based
              only on the information found in
              your resume.
            </p>

            {aiStatus ===
              "processing" && (
              <div className="ai-loading">
                🤖 AI is reviewing your resume...
              </div>
            )}

            {aiAdvice &&
              aiAdvice.success && (
                <div className="feedback-content">
                  <div className="feedback-block">
                    <h3>
                      Overall Advice
                    </h3>

                    <p>
                      {aiAdvice.overall_advice}
                    </p>
                  </div>

                  {aiAdvice.high_priority_issues
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🔴 High Priority
                      </h3>

                      <ul>
                        {aiAdvice.high_priority_issues.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.medium_priority_issues
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🟡 Medium Priority
                      </h3>

                      <ul>
                        {aiAdvice.medium_priority_issues.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.strengths
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🟢 Strengths
                      </h3>

                      <ul>
                        {aiAdvice.strengths.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.actionable_suggestions
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🎯 Actionable Suggestions
                      </h3>

                      <ul>
                        {aiAdvice.actionable_suggestions.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )}

            {aiStatus ===
              "failed" && (
              <p className="muted">
                AI advisor could not complete
                right now. Your rule-based report
                is still available.
              </p>
            )}
          </section>

          {/* AI CHAT */}

          <section className="report-card">
            <div className="card-heading">
              <span>💬</span>
              AI Career Chat
            </div>

            <p className="muted">
              Ask anything about this resume in
              English, Hindi or Hinglish.
            </p>

            <div className="chat-box">
              <div className="chat-messages">
                {chatMessages.length ===
                  0 && (
                  <div className="chat-empty">
                    💬 Ask your first question
                    about the resume.
                  </div>
                )}

                {chatMessages.map(
                  (
                    message,
                    index
                  ) => (
                    <div
                      className={`chat-message ${message.role}`}
                      key={index}
                    >
                      <div className="chat-role">
                        {message.role ===
                        "user"
                          ? "You"
                          : "ResumeAI"}
                      </div>

                      <div className="chat-text">
                        {message.text}
                      </div>
                    </div>
                  )
                )}

                {chatLoading && (
                  <div className="chat-message assistant">
                    <div className="chat-role">
                      ResumeAI
                    </div>

                    <div className="chat-text">
                      🤖 Thinking...
                    </div>
                  </div>
                )}
              </div>

              <div className="chat-input-row">
                <textarea
                  value={chatInput}
                  onChange={(event) =>
                    setChatInput(
                      event.target.value
                    )
                  }
                  onKeyDown={
                    handleChatKeyDown
                  }
                  placeholder="Ask about your resume..."
                  rows={2}
                  disabled={
                    chatLoading
                  }
                />

                <button
                  onClick={
                    sendChatMessage
                  }
                  disabled={
                    chatLoading ||
                    !chatInput.trim()
                  }
                >
                  Send
                </button>
              </div>
            </div>
          </section>

          {/* ACTION PLAN */}

          <section className="report-card">
            <div className="card-heading">
              <span>🎯</span>
              Action Plan
            </div>

            {actionPlan.length >
            0 ? (
              <div className="action-plan">
                {actionPlan.map(
                  (
                    item,
                    index
                  ) => (
                    <div
                      className="action-item"
                      key={index}
                    >
                      <div className="action-number">
                        {index + 1}
                      </div>

                      <div>
                        {item}
                      </div>
                    </div>
                  )
                )}
              </div>
            ) : (
              <p className="muted">
                No action items available.
              </p>
            )}
          </section>

          {/* ENHANCE RESUME */}

          <section className="report-card enhance-card">
            <div className="card-heading">
              <span>✨</span>
              Enhance My Resume
            </div>

            <div className="enhance-content">
              <div>
                <h2>
                  Build a more professional
                  resume
                </h2>

                <p>
                  ResumeAI will improve wording,
                  structure and presentation
                  while keeping the factual
                  information from your original
                  resume.
                </p>

                <div className="enhance-features">
                  <span>
                    ✓ Professional formatting
                  </span>

                  <span>
                    ✓ ATS-friendly structure
                  </span>

                  <span>
                    ✓ Stronger wording
                  </span>

                  <span>
                    ✓ Clean bullet points
                  </span>

                  <span>
                    ✓ Original facts preserved
                  </span>

                  <span>
                    ✓ Photo preserved when
                    available
                  </span>
                </div>
              </div>

              {!showEnhancePhotoOptions &&
                !enhancedResume && (
                  <button
                    className="enhance-button"
                    onClick={
                      handleEnhanceClick
                    }
                    disabled={
                      enhancing ||
                      checkingPhoto
                    }
                  >
                    {checkingPhoto
                      ? "Checking Resume..."
                      : enhancing
                        ? "Creating Resume..."
                        : "Enhance Resume →"}
                  </button>
                )}
            </div>

            {originalPhotoDetected ===
              true &&
              enhancing && (
                <div className="enhance-info">
                  📷 Profile photo detected in
                  your original resume. It will
                  be preserved automatically.
                </div>
              )}

            {showEnhancePhotoOptions &&
              !enhancedResume && (
                <div className="enhance-photo-options">
                  <div className="enhance-photo-header">
                    <h3>
                      Profile Photo
                      <span>
                        {" "}
                        (Optional)
                      </span>
                    </h3>

                    <p>
                      No profile photo was detected
                      in your original resume. You
                      can add one or continue without
                      a photo.
                    </p>
                  </div>

                  <div className="enhance-photo-actions">
                    <label className="photo-button">
                      {photo
                        ? "Change Photo"
                        : "Add Photo"}

                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png"
                        onChange={
                          handlePhotoChange
                        }
                        hidden
                      />
                    </label>

                    <button
                      type="button"
                      className="enhance-button"
                      onClick={
                        skipPhotoAndEnhance
                      }
                      disabled={
                        enhancing
                      }
                    >
                      {enhancing
                        ? "Creating PDF..."
                        : "Skip Photo & Enhance"}
                    </button>
                  </div>

                  {photoPreview && (
                    <div className="photo-preview-wrap">
                      <img
                        src={photoPreview}
                        alt="Selected profile preview"
                        className="photo-preview"
                      />

                      <button
                        type="button"
                        className="enhance-button"
                        onClick={
                          addPhotoAndEnhance
                        }
                        disabled={
                          enhancing
                        }
                      >
                        {enhancing
                          ? "Creating PDF..."
                          : "Create Enhanced Resume"}
                      </button>
                    </div>
                  )}
                </div>
              )}

            {enhanceError && (
              <div className="enhance-error">
                {enhanceError}
              </div>
            )}

            {enhancedResume && (
              <div className="enhanced-result">
                <div className="enhanced-result-header">
                  <div>
                    <h3>
                      ✨ Professional Resume
                    </h3>

                    <p>
                      Your enhanced resume is
                      ready for review.
                    </p>
                  </div>

                  <button
                    className="download-button"
                    onClick={
                      downloadEnhancedPDF
                    }
                  >
                    ⬇ Download Professional
                    PDF
                  </button>
                </div>

                <div className="resume-paper">
                  {renderEnhancedPreview(
                    enhancedResume
                  )}
                </div>
              </div>
            )}
          </section>
        </main>
      )}
      </div>}
      </div>
    </div>
  );
}

export default App;

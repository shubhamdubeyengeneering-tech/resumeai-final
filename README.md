# ResumeAI 3.0

AI Resume Analyzer + Career Workspace built with React/Vite and FastAPI.

## Features
- Resume-only validation with honest deterministic scoring
- PDF/DOC/DOCX/RTF/ODT/TXT and common image resume extraction
- OCR fallback for scanned resumes
- Grounded Gemini AI feedback
- Multilingual AI Career Chat and adaptive mock interviews (English/Hindi/Hinglish)
- Voice input/output with voice preview and device-aware male/female preference fallback
- Live jobs from multiple providers, resume matching and country/work-mode filters
- Auto-saving settings + Neon theme
- Optional Google OAuth, Gmail SMTP notifications and 24-hour digest worker
- Optional website PIN lock after login

## Backend
```bash
cd src/backend
pip install -r ../../requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend
```bash
npm install
npm run dev
```

Create `.env` from `.env.example` for the backend. Never commit real API keys or passwords.

### OCR note
Image/scanned-PDF OCR requires the Tesseract executable to be installed on the machine/container.

### Google login
Google OAuth is optional. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` and `RESUMEAI_FRONTEND_URL` after creating an OAuth Web Application in Google Cloud.

### Job coverage
Remotive and Arbeitnow are used without an API key. Adzuna can be enabled with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` for broader country coverage.

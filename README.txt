ResumeAI Advanced — Functional AI Update

This build keeps the existing ResumeAI UI/features and adds:
- Automatic Settings saving with debounce.
- Dashboard search navigation.
- Resume-based live job matching and filters (role, resume skill, experience, location).
- Persistent resume text/job context so Jobs, Mocks and Career Chat can still use the analyzed resume after refresh/backend restart.
- AI Career Chat conversation history and ResumeAI feature context.
- Mock interviews linked to target role + target goal + analyzed resume, with AI-generated adaptive non-repeating questions.
- Broader resume upload formats: PDF, DOCX, JPG, JPEG, PNG, WEBP and TXT.
- Persistent resume validation remains in place to reject common non-resume documents such as marksheets/transcripts.

Keep your existing .env file and GEMINI_API_KEY. Never commit .env to GitHub.


ResumeAI 4.9 fixes applied: PDF/image OCR fallback, guest identity isolation, persistent Hindi UI language, dark-mode readability, enhanced preview text contrast, Gemini low-thinking fast path with fallback model.

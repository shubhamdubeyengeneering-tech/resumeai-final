# ResumeAI diagnostic and AI fixes (18 Nov 2026)

Changes applied to the supplied `ResumeAI_SEARCH_AI_VOICE_FIXED.zip` source:

1. Gemini 3.x request compatibility: removed the legacy `temperature` field from the generation config. Current Gemini 3.8 Flash guidance says not to send temperature/top-p/top-k sampling controls.
2. Added `POST /ai-health/test`, which sends a small real Gemini request and returns a credential-free success/error response. `GET /ai-health` remains a configuration-only check and now says so explicitly.
3. AI Career Advisor now displays the backend failure message returned by `/ai-feedback/{job_id}` rather than hiding it behind the generic rule-based fallback text.
4. Resume Enhancer now returns a sanitized underlying failure message instead of always replacing it with a generic message. The API key is redacted from returned error text.
5. Existing voice behavior is retained: it only selects an installed voice whose name clearly matches the requested gender and language; it warns instead of silently choosing the opposite gender. Actual voice availability still depends on the Windows/browser installed voices.

Validation performed:
- `python -m py_compile src/backend/main.py` passed.
- Full Vite build was not verified: `npm install` timed out in this environment. Install dependencies and run `npm run build` locally before deployment.
- Gemini live generation was not tested because the user's API credential is intentionally not available in this workspace.

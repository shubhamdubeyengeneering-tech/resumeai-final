# ResumeAI – Mock Interview Hindi Voice Fix

## Changes made
- Replaced the Mock Interview Hindi question bank with natural Hindi written in Devanagari (not Romanized Hinglish).
- Added Hindi-specific fallback questions for software, data, and general roles, including when no resume is uploaded.
- Added strict language validation for the first and subsequent questions. The backend no longer silently falls back to an English question during a Hindi interview.
- Made browser speech synthesis use the active mock session's selected language. The website-wide language setting can no longer override the interview language.
- Added the session language to the voice auto-play effect dependencies so the first question is spoken with the correct locale.
- Kept English interview behavior and existing interview flow intact.

## Checks
- Python syntax compilation passed for `main.py`, `features.py`, and `auth.py`.
- Frontend production build was not run because this source ZIP does not include `node_modules`; install dependencies and run `npm run build` locally.
- Actual Hindi voice availability depends on the browser/device. The app requests `hi-IN` and only attaches a voice whose locale starts with `hi`; if no Hindi voice is installed, the browser's Hindi locale fallback is used. Install/enable a Hindi speech voice on the device for best voice quality.

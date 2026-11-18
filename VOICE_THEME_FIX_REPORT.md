# ResumeAI voice, theme and feature cleanup

## Changes made
- Removed the added Career Lab and Resume Health Center pages and their route mounts/state. Existing Resume Analyzer scoring and other unrelated features were left in place.
- Kept the established Light and Dark appearance choices only. Removed Ocean/Forest from the frontend theme state and backend theme validation so stale values fall back to Light.
- Persisted voice gender, Test Voice language and voice-enabled preference in local storage so the separate Mock Interview page reads the same settings after navigation.
- For signed-in users, Mock Interview also reloads saved voice preferences from the account settings API, including when starting an interview.
- Mock Interview speech language follows the language selected in the Mock Interview setup (English or Hindi). The voice gender follows the setting selected in AI Preferences.
- Test Voice uses its own English/Hindi test-language selection and the same selected gender.
- Voice selection now filters by both language and recognizable voice-name hints for the requested gender. It no longer silently falls back to an opposite-gender or unknown-gender voice; it shows a warning when the device/browser does not expose a clearly identifiable matching voice.
- Existing page layout and CSS were not broadly redesigned. The existing Dark theme contrast rules were retained.

## Important platform limitation
The browser SpeechSynthesis API does not provide a standardized male/female field for installed voices. ResumeAI can select installed voices whose names identify a likely gender, but it cannot guarantee the perceived gender of every vendor voice. Some devices expose generic names such as “Google हिन्दी”; for those, the app warns instead of claiming a gender match or silently selecting the opposite voice. Available voices depend on the user's OS, browser and installed speech packs.

## Validation
- `src/backend/main.py`, `src/backend/auth.py` and `src/backend/features.py` passed Python syntax compilation.
- `src/App.jsx` passed TypeScript's JSX parser syntax check.
- A full Vite production build was not run because `npm install --no-audit --no-fund` timed out in this environment; no frontend build success is claimed.
- Actual audio gender/language behavior still needs to be tested on the target Android/browser device because its installed speech voices are device-specific.

# ResumeAI v5.8 — Reference-inspired UI and stability work

## Changes
- Theme initialization now reads the saved theme from localStorage instead of always starting at Light.
- Settings hydration prioritizes the user's locally saved theme to prevent stale server settings from resetting the active palette.
- Added a cohesive reference-inspired visual layer: navy workspace sidebar, bright blue primary actions, cleaner card surfaces, spacing, borders, shadows and responsive layout.
- Added coordinated Light, Dark, Ocean and Forest palette overrides for shared workspace modules.
- Resume Health now uses a broader, transparent 10-point content checklist, including contact format, section evidence, measurable outcomes, readability and role relevance. Its score is labeled checklist coverage, not an ATS prediction.
- Career Lab now persists job descriptions and compares normalized meaningful tokens while excluding common stop words; common skill aliases are normalized.

## Verification
- Source files and ZIP archive integrity are checked.
- `npm install` could not complete in this environment (dependency installation timed out), so `npm run build` could not be run because Vite is not installed. Do not treat this build as fully verified.

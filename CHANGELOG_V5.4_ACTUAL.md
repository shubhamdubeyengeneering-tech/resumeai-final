# ResumeAI v5.4 - Actual Changes

- Added four workspace themes: Light Professional, Dark Professional, Ocean Blue, and Forest Green.
- Added real Appearance controls to Settings; theme selection persists in localStorage and backend settings.
- Added Ocean/Forest theme classes to the application shell and key cards.
- Enabled Hindi in Website Language selector; removed the effect that forced English after selection.
- Improved theme hydration so valid themes survive page changes and refreshes.
- Changed PIN setup to enable Website Lock immediately after a successful PIN creation.
- Preserved PIN verification, change, disable, and remove flows.
- Added stricter resume scoring quality gates: missing metrics, low action-verb evidence, short content, and low skill coverage reduce score ceilings.
- Photo presence is not required for scoring.
- Preserved Career Lab and Resume Health pages and existing project structure.

Validation completed:
- Python syntax compilation passed for main.py, features.py, and auth.py.
- npm install/build could not be completed in the environment because npm install timed out; run `npm install` and `npm run build` locally before deployment.

# ResumeAI voice and navigation update

## Changes
- Added a separate Test Voice language selector (English/Hindi) in Settings > AI Preferences.
- Test Voice now speaks the exact selected test language instead of inheriting the Mock Interview language.
- Added `voice_language` to backend settings storage, including a safe SQLite migration for existing databases.
- Voice playback filters installed browser voices by requested language and prefers a voice whose name suggests the selected gender; pitch is used only as a fallback.
- Removed Career Lab and Resume Health from the top navigation and sidebar navigation.
- Replaced the top-bar and sidebar robot-face brand marks with a softer sparkle mark.

## Important browser limitation
The Web Speech API does not expose a standard male/female property for voices. ResumeAI can prefer installed voices whose names indicate the requested gender and adjust pitch as a fallback, but it cannot guarantee male/female timbre if the device/browser does not provide a suitable voice. The settings UI explains this.

## Validation
- Python backend files pass `py_compile`.
- Frontend production build was not completed: `npm install` did not finish within the available time, so no browser-level voice test is claimed.

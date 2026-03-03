# CLAUDE.md — EchoType

## Architecture

Single-process PyQt5 desktop app. No database, no server. All state lives in memory; config persists to JSON.

### State Machine (app.py)

```
IDLE → (hotkey) → RECORDING → (hotkey) → TRANSCRIBING → clipboard
IDLE → (enhance hotkey) → RECORDING → (hotkey) → TRANSCRIBING → ENHANCING → clipboard
Any RECORDING state → (Escape) → IDLE (cancelled)
```

### Threading Model

- **Main thread**: Qt event loop, UI, state machine
- **Audio callback**: sounddevice background thread → appends frames to list (thread-safe via Lock)
- **TranscriptionWorker**: QThread → calls OpenAI Whisper API → emits signal back to main thread
- **PromptEnhanceWorker**: QThread → calls OpenAI Chat API → emits signal back to main thread

**Critical rule**: Never access Qt widgets from background threads. Use `pyqtSignal` to communicate back.

### Signal names

Do NOT name signals `finished` on QThread subclasses — it shadows `QThread.finished` and causes crashes. Use `result_ready` / `error` instead.

### Security — DPAPI

API keys are encrypted at rest via Windows DPAPI (`dpapi.py`). The `config.py` module auto-encrypts on save and decrypts on read via `Config.get_api_key()`. Never call `config.get('api_key')` directly — it returns the encrypted blob.

## Conventions

- Python 3.10+, PyQt5
- Logging: per-module loggers (`echotype.app`, `echotype.recorder`, etc.)
- Config: `Config.get(key)` falls back to DEFAULTS; `Config.get_api_key()` for API key; `Config.update({...})` for batch saves
- Style: cyberpunk/hacker theme — neon green (#00ff41), dark backgrounds
- No type annotations on simple functions; use them only where they add clarity
- Minimize dependencies — currently: PyQt5, sounddevice, numpy, openai, keyboard

## Build

```bash
pyinstaller EchoType.spec --clean
```

Output: `dist/EchoType.exe` (single-file, ~60MB). The spec file has an extensive `excludes` list to reduce size.

## File Locations

- Config: `%APPDATA%/EchoType/config.json`
- Log: `%APPDATA%/EchoType/echotype.log` (rotating, 2MB max, 3 backups)
- Temp audio: `%TEMP%/tmp*.wav` (cleaned up after transcription; orphans cleaned on startup)

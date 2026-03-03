# EchoType

Windows system tray application that records voice, transcribes it via OpenAI Whisper API, and copies the result to clipboard. Includes a **Prompt Enhance** mode that passes transcription through GPT-4o to produce a polished AI prompt.

## Features

- **Voice to clipboard** — press hotkey, speak, press again, text is in clipboard
- **Prompt enhance mode** — second hotkey records + transcribes + enhances via GPT-4o
- **Cyberpunk overlay** — real-time audio level bars, animated processing states
- **Configurable** — hotkeys, Whisper model, language, enhance model & system prompt
- **Encrypted API key** — your OpenAI key is encrypted at rest using Windows DPAPI
- **Single-file exe** — no installation required (or use the Inno Setup installer)

## Requirements

- Python 3.10+
- Windows 10/11
- OpenAI API key

## Setup

```bash
pip install -r requirements.txt
python main.py
```

On first launch, the Settings window opens automatically to enter your API key.

## Usage

| Action | Default Hotkey |
|---|---|
| Record & transcribe | `Ctrl+Shift+Space` |
| Record & enhance prompt | `Ctrl+Shift+X` |
| Cancel recording | `Escape` |

All hotkeys are configurable in Settings (right-click tray icon).

## Build

```bash
# Build single-file exe
build.bat

# Output: dist/EchoType.exe
```

Optionally build an installer with [Inno Setup](https://jrsoftware.org/isinfo.php) using `installer.iss`.

## Project Structure

```
main.py              Entry point, logging, exception hooks
config.py            JSON config persistence (%APPDATA%/EchoType/)
dpapi.py             Windows DPAPI encryption for API key storage
app.py               State machine, hotkey registration, tray icon
recorder.py          Audio capture via sounddevice
transcriber.py       OpenAI Whisper + GPT-4o workers (QThread)
overlay.py           Cyberpunk-styled floating overlay
settings_window.py   Settings UI
generate_icon.py     Build-time icon generator
```

## Security

Your OpenAI API key is encrypted at rest using [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/) (`CryptProtectData` / `CryptUnprotectData`). The ciphertext is tied to your Windows user account — only your login can decrypt it. The encrypted key is stored in `%APPDATA%/EchoType/config.json`.

If you migrate the config file to another machine or user account, you will need to re-enter your API key.

## Changelog

### v1.0.0

- Initial public release
- API key encryption via Windows DPAPI
- MIT license

## License

[MIT](LICENSE)

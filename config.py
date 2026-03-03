import json
import logging
import os
from pathlib import Path

from dpapi import encrypt_string, decrypt_string

log = logging.getLogger('echotype.config')

_APPDATA = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
CONFIG_DIR = _APPDATA / 'EchoType'
CONFIG_FILE = CONFIG_DIR / 'config.json'

CONFIG_VERSION = 3

DEFAULT_ENHANCE_PROMPT = (
    'You are an expert prompt engineer. Take the user\'s rough idea and transform it '
    'into a clear, detailed, professional prompt for an AI coding assistant. Keep the '
    'original intent, add structure, context and specific instructions. Respond only '
    'with the improved prompt, no explanations.'
)

DEFAULTS = {
    'config_version': CONFIG_VERSION,
    'api_key': '',
    'api_key_encrypted': False,
    'hotkey': 'ctrl+shift+space',
    'model': 'whisper-1',
    'language': '',
    'autostart': False,
    'enhance_hotkey': 'ctrl+shift+x',
    'enhance_model': 'gpt-4o',
    'enhance_system_prompt': DEFAULT_ENHANCE_PROMPT,
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self._data.update(saved)
                # Remove keys that no longer exist in DEFAULTS (stale cleanup)
                stale = set(self._data) - set(DEFAULTS)
                for key in stale:
                    del self._data[key]
                self._data['config_version'] = CONFIG_VERSION

                # Migrate: encrypt plaintext API key on load
                if self._data.get('api_key') and not self._data.get('api_key_encrypted'):
                    self._encrypt_and_store(self._data['api_key'])
        except Exception:
            log.exception('Failed to load config')

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def get_api_key(self):
        """Return the plaintext API key, decrypting if necessary."""
        raw = self._data.get('api_key', '')
        if not raw:
            return ''
        if self._data.get('api_key_encrypted'):
            try:
                return decrypt_string(raw)
            except Exception:
                log.exception('Failed to decrypt API key')
                return ''
        return raw

    def set(self, key, value):
        if key == 'api_key' and value:
            self._encrypt_and_store(value)
            return
        self._data[key] = value
        self.save()

    def update(self, mapping):
        """Set multiple keys and save once (avoids repeated disk writes)."""
        api_key = mapping.pop('api_key', None)
        self._data.update(mapping)
        if api_key:
            self._encrypt_and_store(api_key)
        else:
            self.save()

    def _encrypt_and_store(self, plaintext):
        """Encrypt an API key via DPAPI and save."""
        try:
            self._data['api_key'] = encrypt_string(plaintext)
            self._data['api_key_encrypted'] = True
            log.info('API key encrypted via DPAPI')
        except Exception:
            log.exception('DPAPI encryption failed, storing key as plaintext')
            self._data['api_key'] = plaintext
            self._data['api_key_encrypted'] = False
        self.save()

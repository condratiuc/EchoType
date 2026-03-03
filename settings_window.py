import sys
import winreg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QCheckBox, QGroupBox, QFormLayout, QTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence

from config import Config, DEFAULT_ENHANCE_PROMPT


LANGUAGES = [
    ('', 'Auto-detect'),
    ('en', 'English'),
    ('ru', 'Russian'),
    ('uk', 'Ukrainian'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
    ('it', 'Italian'),
    ('pt', 'Portuguese'),
    ('zh', 'Chinese'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('ar', 'Arabic'),
    ('hi', 'Hindi'),
    ('pl', 'Polish'),
    ('tr', 'Turkish'),
]

MODELS = [
    'whisper-1',
    'gpt-4o-transcribe',
    'gpt-4o-mini-transcribe',
]

ENHANCE_MODELS = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4.1',
    'gpt-4.1-mini',
    'gpt-4.1-nano',
]

STARTUP_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
APP_NAME = 'EchoType'

# ── Cyberpunk / Hacker Theme ──────────────────────────────────────────
NEON = '#00ff41'
CYAN = '#00d4ff'
BG = '#0a0e14'
BG_CARD = '#111820'
BG_INPUT = '#0d1117'
BORDER = '#1a2332'
TEXT = '#c5d1de'
TEXT_DIM = '#4a5568'
RED = '#ff3344'
MONO = 'Consolas'

STYLESHEET = f"""
QWidget#SettingsRoot {{
    background-color: {BG};
}}

QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 18px 14px 12px 14px;
    font-family: {MONO};
    font-size: 11px;
    color: {NEON};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {NEON};
    font-family: {MONO};
    font-weight: bold;
    font-size: 11px;
}}

QLabel {{
    color: {TEXT};
    font-family: {MONO};
    font-size: 11px;
}}

QLineEdit, QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 7px 10px;
    font-family: {MONO};
    font-size: 11px;
    selection-background-color: #1a3a2a;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {NEON};
}}
QLineEdit::placeholder {{
    color: {TEXT_DIM};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {NEON};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {NEON};
    selection-background-color: #0d2818;
    selection-color: {NEON};
    font-family: {MONO};
    outline: none;
}}

QCheckBox {{
    color: {TEXT};
    font-family: {MONO};
    font-size: 11px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: #0d2818;
    border-color: {NEON};
}}

QTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 7px 10px;
    font-family: {MONO};
    font-size: 11px;
    selection-background-color: #1a3a2a;
}}
QTextEdit:focus {{
    border: 1px solid {NEON};
}}

QPushButton {{
    font-family: {MONO};
    font-size: 11px;
    font-weight: bold;
    border-radius: 4px;
    padding: 8px 20px;
}}
QPushButton#SaveBtn {{
    background-color: transparent;
    color: {NEON};
    border: 1px solid {NEON};
}}
QPushButton#SaveBtn:hover {{
    background-color: #0d2818;
}}
QPushButton#SaveBtn:pressed {{
    background-color: #0a1f14;
}}
QPushButton#CancelBtn {{
    background-color: transparent;
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
}}
QPushButton#CancelBtn:hover {{
    color: {TEXT};
    border-color: {TEXT_DIM};
}}
"""


class HotkeyEdit(QLineEdit):
    """Custom line-edit that captures a key combination."""

    def __init__(self, text=''):
        super().__init__(text)
        self.setReadOnly(True)
        self.setPlaceholderText('> click, then press keys...')
        self._capturing = False

    def mousePressEvent(self, event):
        self._capturing = True
        self.setText('awaiting input...')
        self.setStyleSheet(f'border: 1px solid {CYAN}; color: {CYAN};')
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            return

        key = event.key()
        mods = event.modifiers()

        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        parts = []
        if mods & Qt.ControlModifier:
            parts.append('ctrl')
        if mods & Qt.AltModifier:
            parts.append('alt')
        if mods & Qt.ShiftModifier:
            parts.append('shift')

        key_name = QKeySequence(key).toString().lower()
        if key_name:
            parts.append(key_name)

        if parts:
            self.setText('+'.join(parts))

        self._capturing = False
        self.setStyleSheet('')

    def focusOutEvent(self, event):
        self._capturing = False
        self.setStyleSheet('')
        super().focusOutEvent(event)


class SettingsWindow(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        self.setObjectName('SettingsRoot')
        self.setWindowTitle('EchoType')
        self.setFixedSize(440, 680)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel('ECHO_TYPE')
        header.setFont(QFont(MONO, 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f'color: {NEON}; letter-spacing: 2px;')
        root.addWidget(header)

        ver_label = QLabel('v1.0.0  //  voice > clipboard')
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet(f'color: {TEXT_DIM}; font-size: 10px; margin-bottom: 4px;')
        root.addWidget(ver_label)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f'background-color: {BORDER};')
        root.addWidget(sep)

        # API group
        api_group = QGroupBox('// OPENAI_API')
        api_form = QFormLayout(api_group)
        api_form.setSpacing(8)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText('sk-...')
        api_form.addRow('api_key:', self.api_key_edit)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        for m in MODELS:
            self.model_combo.addItem(m)
        api_form.addRow('model:', self.model_combo)

        self.lang_combo = QComboBox()
        for code, name in LANGUAGES:
            self.lang_combo.addItem(name, code)
        api_form.addRow('language:', self.lang_combo)

        root.addWidget(api_group)

        # Hotkey group
        hk_group = QGroupBox('// HOTKEY')
        hk_layout = QHBoxLayout(hk_group)
        self.hotkey_edit = HotkeyEdit()
        hk_layout.addWidget(self.hotkey_edit)
        root.addWidget(hk_group)

        # Prompt Enhance group
        enhance_group = QGroupBox('// PROMPT_ENHANCE')
        enhance_layout = QVBoxLayout(enhance_group)
        enhance_layout.setSpacing(8)

        hk2_row = QHBoxLayout()
        hk2_label = QLabel('hotkey:')
        self.enhance_hotkey_edit = HotkeyEdit()
        hk2_row.addWidget(hk2_label)
        hk2_row.addWidget(self.enhance_hotkey_edit)
        enhance_layout.addLayout(hk2_row)

        model_row = QHBoxLayout()
        model_label = QLabel('model:')
        self.enhance_model_combo = QComboBox()
        self.enhance_model_combo.setEditable(True)
        for m in ENHANCE_MODELS:
            self.enhance_model_combo.addItem(m)
        model_row.addWidget(model_label)
        model_row.addWidget(self.enhance_model_combo)
        enhance_layout.addLayout(model_row)

        sp_label = QLabel('system_prompt:')
        enhance_layout.addWidget(sp_label)

        self.enhance_prompt_edit = QTextEdit()
        self.enhance_prompt_edit.setFixedHeight(70)
        self.enhance_prompt_edit.setPlaceholderText('System prompt for enhancement...')
        enhance_layout.addWidget(self.enhance_prompt_edit)

        root.addWidget(enhance_group)

        # Autostart
        self.autostart_check = QCheckBox('autostart_with_windows')
        root.addWidget(self.autostart_check)

        root.addStretch()

        # Status line
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f'color: {TEXT_DIM}; font-size: 10px;')
        root.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.save_btn = QPushButton('[ SAVE ]')
        self.save_btn.setObjectName('SaveBtn')
        self.save_btn.setFixedWidth(110)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        self.cancel_btn = QPushButton('[ EXIT ]')
        self.cancel_btn.setObjectName('CancelBtn')
        self.cancel_btn.setFixedWidth(110)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.close)
        btn_row.addWidget(self.cancel_btn)

        root.addLayout(btn_row)

    def _load_values(self):
        self.api_key_edit.setText(self.config.get_api_key())
        self.model_combo.setCurrentText(self.config.get('model'))
        self.hotkey_edit.setText(self.config.get('hotkey'))
        self.enhance_hotkey_edit.setText(self.config.get('enhance_hotkey'))
        self.enhance_model_combo.setCurrentText(self.config.get('enhance_model'))
        self.enhance_prompt_edit.setPlainText(
            self.config.get('enhance_system_prompt') or DEFAULT_ENHANCE_PROMPT
        )
        self.autostart_check.setChecked(self.config.get('autostart'))

        lang = self.config.get('language')
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == lang:
                self.lang_combo.setCurrentIndex(i)
                break

    def _on_save(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            self.status_label.setStyleSheet(f'color: {RED}; font-size: 10px;')
            self.status_label.setText('ERR: api_key is required')
            return

        hotkey = self.hotkey_edit.text().strip()
        if not hotkey or hotkey == 'awaiting input...':
            self.status_label.setStyleSheet(f'color: {RED}; font-size: 10px;')
            self.status_label.setText('ERR: hotkey is required')
            return

        enhance_hotkey = self.enhance_hotkey_edit.text().strip()
        if not enhance_hotkey or enhance_hotkey == 'awaiting input...':
            enhance_hotkey = 'ctrl+shift+x'

        enhance_prompt = self.enhance_prompt_edit.toPlainText().strip()
        if not enhance_prompt:
            enhance_prompt = DEFAULT_ENHANCE_PROMPT

        # Batch save — writes config file once instead of per-key
        self.config.update({
            'api_key': api_key,
            'model': self.model_combo.currentText(),
            'language': self.lang_combo.currentData(),
            'hotkey': hotkey,
            'enhance_hotkey': enhance_hotkey,
            'enhance_model': self.enhance_model_combo.currentText(),
            'enhance_system_prompt': enhance_prompt,
            'autostart': self.autostart_check.isChecked(),
        })

        self._apply_autostart(self.autostart_check.isChecked())

        self.status_label.setStyleSheet(f'color: {NEON}; font-size: 10px;')
        self.status_label.setText('config saved.')

        self.settings_saved.emit()
        self.close()

    def _apply_autostart(self, enable):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, STARTUP_KEY,
                0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            )
            if enable:
                exe = sys.executable
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except OSError:
            pass

    def closeEvent(self, event):
        event.accept()

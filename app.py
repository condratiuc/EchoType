import sys
import logging
import keyboard
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QIcon

from config import Config
from recorder import AudioRecorder
from transcriber import TranscriptionWorker, PromptEnhanceWorker
from overlay import RecordingOverlay
from settings_window import SettingsWindow

log = logging.getLogger('echotype.app')


def _make_icon(color: str = '#ffffff', recording: bool = False) -> QIcon:
    """Draw a simple microphone icon programmatically."""
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(QColor(color))
    pen.setWidth(3)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # mic body
    p.drawRoundedRect(22, 8, 20, 28, 10, 10)
    # arc
    p.drawArc(14, 18, 36, 28, 0, -180 * 16)
    # stand
    p.drawLine(32, 46, 32, 54)
    p.drawLine(22, 54, 42, 54)

    if recording:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(239, 68, 68))
        p.drawEllipse(46, 4, 14, 14)

    p.end()
    return QIcon(px)


class HotkeyBridge(QObject):
    triggered = pyqtSignal()


class EchoTypeApp(QObject):
    STATE_IDLE = 'idle'
    STATE_RECORDING = 'recording'
    STATE_TRANSCRIBING = 'transcribing'
    STATE_ENHANCING = 'enhancing'

    def __init__(self):
        self.app = QApplication(sys.argv)
        super().__init__()
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName('EchoType')

        self.config = Config()
        self.recorder = AudioRecorder()
        self.overlay = RecordingOverlay()
        self.settings_win = None
        self.state = self.STATE_IDLE

        self._hotkey_bridge = HotkeyBridge()
        self._hotkey_bridge.triggered.connect(self._toggle, Qt.QueuedConnection)

        self._enhance_hotkey_bridge = HotkeyBridge()
        self._enhance_hotkey_bridge.triggered.connect(self._toggle_enhance, Qt.QueuedConnection)

        self._cancel_bridge = HotkeyBridge()
        self._cancel_bridge.triggered.connect(self._cancel_recording, Qt.QueuedConnection)

        self._hotkey_hook = None
        self._enhance_hotkey_hook = None
        self._cancel_hook = None
        self._worker = None
        self._enhance_worker = None
        self._enhance_mode = False

        # Timer to poll audio level from recorder
        self._level_timer = QTimer()
        self._level_timer.setInterval(50)
        self._level_timer.timeout.connect(self._poll_level)

        # Shared animation timer for transcribing/enhancing overlay dots
        self._animation_timer = QTimer()
        self._animation_timer.setInterval(300)
        self._animation_timer.timeout.connect(self._animation_tick)

        self._icons = {
            'idle': _make_icon('#ffffff'),
            'recording': _make_icon('#ef4444', recording=True),
            'transcribing': _make_icon('#60a5fa'),
            'enhancing': _make_icon('#c084fc'),
        }

        self._setup_tray()
        self._register_hotkey()

        # First launch: open settings if no API key
        if not self.config.get_api_key():
            QTimer.singleShot(500, self._show_settings)

        log.info('EchoTypeApp initialised (state=%s)', self.state)

    # --- common helpers ---

    def _reset_to_idle(self):
        """Reset state, tray icon and tooltip to idle. Stops animation timer."""
        self._animation_timer.stop()
        self.state = self.STATE_IDLE
        self.tray.setIcon(self._icons['idle'])
        self.tray.setToolTip('EchoType — Ready')

    # --- system tray ---

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self._icons['idle'])
        self.tray.setToolTip('EchoType — Ready')
        self.tray.activated.connect(self._on_tray_activated)

        menu = QMenu()
        act_settings = menu.addAction('Settings')
        act_settings.triggered.connect(self._show_settings)
        menu.addSeparator()
        act_quit = menu.addAction('Quit')
        act_quit.triggered.connect(self._quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # left click
            self._toggle()

    # --- hotkey ---

    def _register_hotkey(self):
        # Unregister existing hotkeys
        for hook_attr in ('_hotkey_hook', '_enhance_hotkey_hook', '_cancel_hook'):
            hook = getattr(self, hook_attr)
            if hook is not None:
                try:
                    keyboard.remove_hotkey(hook)
                except (ValueError, KeyError):
                    pass
                setattr(self, hook_attr, None)

        # Register transcription hotkey
        hotkey = self.config.get('hotkey')
        if hotkey:
            try:
                self._hotkey_hook = keyboard.add_hotkey(
                    hotkey,
                    lambda: self._safe_emit(self._hotkey_bridge),
                    suppress=True,
                )
                log.info('Hotkey registered: %s', hotkey)
            except Exception:
                log.exception('Failed to register hotkey "%s"', hotkey)

        # Register enhance hotkey
        enhance_hotkey = self.config.get('enhance_hotkey')
        if enhance_hotkey:
            try:
                self._enhance_hotkey_hook = keyboard.add_hotkey(
                    enhance_hotkey,
                    lambda: self._safe_emit(self._enhance_hotkey_bridge),
                    suppress=True,
                )
                log.info('Enhance hotkey registered: %s', enhance_hotkey)
            except Exception:
                log.exception('Failed to register enhance hotkey "%s"', enhance_hotkey)

        # Register cancel hotkey (Escape)
        try:
            self._cancel_hook = keyboard.add_hotkey(
                'escape',
                lambda: self._safe_emit(self._cancel_bridge),
            )
            log.info('Cancel hotkey registered: escape')
        except Exception:
            log.exception('Failed to register cancel hotkey')

    def _safe_emit(self, bridge):
        """Wrapper called from keyboard's background thread."""
        try:
            bridge.triggered.emit()
        except Exception:
            log.exception('Error emitting hotkey signal')

    # --- state machine ---

    @pyqtSlot()
    def _toggle_enhance(self):
        log.debug('Toggle enhance called (state=%s)', self.state)
        if self.state == self.STATE_IDLE:
            self._enhance_mode = True
            self._start_recording()
        elif self.state == self.STATE_RECORDING:
            self._stop_recording()

    @pyqtSlot()
    def _toggle(self):
        log.debug('Toggle called (state=%s)', self.state)
        if self.state == self.STATE_IDLE:
            self._enhance_mode = False
            self._start_recording()
        elif self.state == self.STATE_RECORDING:
            self._stop_recording()

    @pyqtSlot()
    def _cancel_recording(self):
        """Cancel recording without transcribing — discard audio."""
        if self.state != self.STATE_RECORDING:
            return
        log.info('Recording cancelled by user')
        self._level_timer.stop()
        try:
            self.recorder.stop()  # saves to temp file
        except Exception:
            log.exception('Error stopping recorder during cancel')
        self._reset_to_idle()
        self.overlay.show_error('Recording cancelled')

    def _start_recording(self):
        if not self.config.get_api_key():
            self.overlay.show_error('Set API key in Settings')
            return

        try:
            self.recorder.start()
        except Exception:
            log.exception('Failed to start recording')
            self.overlay.show_error('Mic error — see logs')
            return

        self.state = self.STATE_RECORDING
        self.tray.setIcon(self._icons['recording'])
        self.tray.setToolTip('EchoType — Recording...')
        self.overlay.show_recording()
        self._level_timer.start()
        log.info('Recording started')

    def _stop_recording(self):
        self._level_timer.stop()

        try:
            audio_path = self.recorder.stop()
        except Exception:
            log.exception('Failed to stop recording')
            audio_path = None

        if not audio_path:
            self._reset_to_idle()
            self.overlay.show_error('No audio recorded')
            log.warning('Recording stopped but no audio file produced')
            return

        self.state = self.STATE_TRANSCRIBING
        self.tray.setIcon(self._icons['transcribing'])
        self.tray.setToolTip('EchoType — Transcribing...')
        self.overlay.show_transcribing()
        self._animation_timer.start()

        self._worker = TranscriptionWorker(
            api_key=self.config.get_api_key(),
            model=self.config.get('model'),
            language=self.config.get('language'),
            audio_path=audio_path,
        )
        self._worker.result_ready.connect(self._on_transcription_done)
        self._worker.error.connect(self._on_transcription_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()
        log.info('Recording stopped, transcription started (%s)', audio_path)

    @pyqtSlot(str)
    def _on_transcription_done(self, text):
        if self._enhance_mode:
            self.state = self.STATE_ENHANCING
            self.tray.setIcon(self._icons['enhancing'])
            self.tray.setToolTip('EchoType — Enhancing...')
            self.overlay.show_enhancing()
            # animation timer already running from transcribing phase

            self._enhance_worker = PromptEnhanceWorker(
                api_key=self.config.get_api_key(),
                text=text,
                system_prompt=self.config.get('enhance_system_prompt'),
                model=self.config.get('enhance_model'),
            )
            self._enhance_worker.result_ready.connect(self._on_enhance_done)
            self._enhance_worker.error.connect(self._on_enhance_error)
            self._enhance_worker.finished.connect(self._cleanup_enhance_worker)
            self._enhance_worker.start()
            log.info('Transcription done, enhancement started (%d chars)', len(text))
            return

        self.app.clipboard().setText(text)
        self._reset_to_idle()
        self.overlay.show_done()
        log.info('Transcription done (%d chars)', len(text))

    @pyqtSlot(str)
    def _on_transcription_error(self, error_text):
        self._reset_to_idle()
        self.overlay.show_error(error_text)
        log.error('Transcription error: %s', error_text)

    @pyqtSlot()
    def _cleanup_worker(self):
        """Called by QThread.finished — the thread has fully stopped, safe to delete."""
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    @pyqtSlot(str)
    def _on_enhance_done(self, text):
        self.app.clipboard().setText(text)
        self._reset_to_idle()
        self.overlay.show_done()
        log.info('Enhancement done (%d chars)', len(text))

    @pyqtSlot(str)
    def _on_enhance_error(self, error_text):
        self._reset_to_idle()
        self.overlay.show_error(error_text)
        log.error('Enhancement error: %s', error_text)

    @pyqtSlot()
    def _cleanup_enhance_worker(self):
        if self._enhance_worker is not None:
            self._enhance_worker.deleteLater()
            self._enhance_worker = None

    # --- helpers ---

    def _poll_level(self):
        if self.state == self.STATE_RECORDING:
            self.overlay.update_level(self.recorder.current_level)

    def _animation_tick(self):
        if self.state in (self.STATE_TRANSCRIBING, self.STATE_ENHANCING):
            self.overlay.update()

    def _show_settings(self):
        if self.settings_win is None or not self.settings_win.isVisible():
            self.settings_win = SettingsWindow(self.config)
            self.settings_win.settings_saved.connect(self._on_settings_saved)
            self.settings_win.show()
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def _on_settings_saved(self):
        self._register_hotkey()

    def _quit(self):
        log.info('Quit requested')
        if self.state == self.STATE_RECORDING:
            self._level_timer.stop()
            try:
                self.recorder.stop()
            except Exception:
                log.exception('Error stopping recorder during quit')
        for hook in (self._hotkey_hook, self._enhance_hotkey_hook, self._cancel_hook):
            if hook is not None:
                try:
                    keyboard.remove_hotkey(hook)
                except (ValueError, KeyError):
                    pass
        self.tray.hide()
        self.app.quit()

    # --- run ---

    def run(self):
        return self.app.exec_()

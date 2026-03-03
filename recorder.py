import glob
import logging
import numpy as np
import os
import sounddevice as sd
import tempfile
import wave
import threading

log = logging.getLogger('echotype.recorder')


def cleanup_orphaned_wavs():
    """Remove leftover tmp*.wav files from previous crashed sessions."""
    pattern = os.path.join(tempfile.gettempdir(), 'tmp*.wav')
    removed = 0
    for path in glob.glob(pattern):
        try:
            os.unlink(path)
            removed += 1
        except OSError:
            pass
    if removed:
        log.info('Cleaned up %d orphaned temp WAV file(s)', removed)


class AudioRecorder:
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = 'int16'

    def __init__(self):
        self.is_recording = False
        self.current_level = 0.0
        self._frames = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self):
        self._frames = []
        self.current_level = 0.0
        self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()
        log.debug('Audio stream opened (rate=%d)', self.SAMPLE_RATE)

    def stop(self):
        self.is_recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                log.exception('Error closing audio stream')
            self._stream = None
        return self._save()

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.warning('Audio callback status: %s', status)
        if not self.is_recording:
            return
        try:
            with self._lock:
                self._frames.append(indata.copy())
            rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            self.current_level = min(1.0, rms / 3000.0)
        except Exception:
            log.exception('Error in audio callback')

    def _save(self):
        with self._lock:
            if not self._frames:
                return None
            audio_data = np.concatenate(self._frames)

        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp_path = tmp.name
        tmp.close()

        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        log.debug('Audio saved to %s (%d frames)', tmp_path, len(audio_data))
        return tmp_path

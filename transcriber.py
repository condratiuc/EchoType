import logging
import os
from openai import OpenAI
from PyQt5.QtCore import QThread, pyqtSignal

log = logging.getLogger('echotype.transcriber')

# Timeout for the OpenAI API call (seconds)
API_TIMEOUT = 120


class TranscriptionWorker(QThread):
    # NOTE: do NOT name these 'finished' — that shadows QThread.finished
    # and breaks thread lifecycle, causing crashes.
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, model, language, audio_path):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.language = language
        self.audio_path = audio_path

    def run(self):
        log.info('Transcription started (model=%s, lang=%s, file=%s)',
                 self.model, self.language or 'auto', self.audio_path)
        try:
            client = OpenAI(api_key=self.api_key, timeout=API_TIMEOUT)
            with open(self.audio_path, 'rb') as f:
                kwargs = {'model': self.model, 'file': f}
                if self.language:
                    kwargs['language'] = self.language
                response = client.audio.transcriptions.create(**kwargs)
            text = response.text.strip()
            if text:
                log.info('Transcription succeeded (%d chars)', len(text))
                self.result_ready.emit(text)
            else:
                log.warning('Transcription returned empty text')
                self.error.emit('Empty transcription — no speech detected')
        except Exception as e:
            log.exception('Transcription failed')
            self.error.emit(str(e))
        finally:
            try:
                os.unlink(self.audio_path)
            except OSError:
                pass


class PromptEnhanceWorker(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, text, system_prompt, model='gpt-4o'):
        super().__init__()
        self.api_key = api_key
        self.text = text
        self.system_prompt = system_prompt
        self.model = model

    def run(self):
        log.info('Prompt enhancement started (model=%s, %d chars input)',
                 self.model, len(self.text))
        try:
            client = OpenAI(api_key=self.api_key, timeout=API_TIMEOUT)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': self.text},
                ],
            )
            result = response.choices[0].message.content.strip()
            if result:
                log.info('Prompt enhancement succeeded (%d chars)', len(result))
                self.result_ready.emit(result)
            else:
                log.warning('Prompt enhancement returned empty text')
                self.error.emit('Enhancement returned empty result')
        except Exception as e:
            log.exception('Prompt enhancement failed')
            self.error.emit(str(e))

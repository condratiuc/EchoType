import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    log_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'EchoType'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'echotype.log'

    handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8',
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    ))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    # also log to stderr so console users see errors
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
    root.addHandler(stderr_handler)

    return log_file


def install_exception_hooks(logger):
    """Catch all unhandled exceptions and log them instead of silently crashing."""

    def excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical('Unhandled exception', exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = excepthook

    # Qt swallows exceptions in slots; monkey-patch to log them
    from PyQt5.QtCore import qInstallMessageHandler, QtCriticalMsg, QtFatalMsg, QtWarningMsg

    def qt_message_handler(mode, context, message):
        if mode == QtFatalMsg:
            logger.critical('Qt fatal: %s (file=%s line=%s)', message, context.file, context.line)
        elif mode == QtCriticalMsg:
            logger.error('Qt critical: %s', message)
        elif mode == QtWarningMsg:
            logger.warning('Qt warning: %s', message)
        else:
            logger.debug('Qt: %s', message)

    qInstallMessageHandler(qt_message_handler)


def main():
    # Ensure the app directory is on the path (needed for PyInstaller)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))

    log_file = setup_logging()
    logger = logging.getLogger('echotype')
    install_exception_hooks(logger)

    logger.info('=== EchoType starting (log: %s) ===', log_file)

    try:
        from recorder import cleanup_orphaned_wavs
        cleanup_orphaned_wavs()

        from app import EchoTypeApp
        app = EchoTypeApp()
        code = app.run()
        logger.info('Application exited with code %s', code)
        sys.exit(code)
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
    except Exception:
        logger.critical('Fatal error during startup or run', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

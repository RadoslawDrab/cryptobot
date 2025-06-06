import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    def __init__(self, name: str, log_file: str = "app.log", level=logging.INFO, max_bytes=1_000_000, backup_count=3):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # Avoid duplicate logs if root logger is set

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)

        # File handler with rotation
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        fh.setLevel(level)
        fh.setFormatter(formatter)

        # Add handlers if not already added
        if not self.logger.handlers:
            self.logger.addHandler(ch)
            self.logger.addHandler(fh)

    def get_logger(self):
        return self.logger
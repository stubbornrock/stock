import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "ebm_monitor.log"

def get_logger(name="EBMMonitor", log_file=LOG_FILE):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        fh = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1,
            backupCount=1, encoding="utf-8"
        )
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger

import logging, os
from dotenv import load_dotenv
load_dotenv()

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))

    # 중복 핸들러 추가 방지
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

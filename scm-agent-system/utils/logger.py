import logging, os, threading
from dotenv import load_dotenv
load_dotenv()

class SlackAlertHandler(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url
        self.setLevel(logging.ERROR)

    def emit(self, record):
        try:
            import requests
            log_entry = self.format(record)
            payload = {
                "text": f"*`[PYTHON BACKEND ERROR]`*\n\n```\n{log_entry}\n```"
            }
            # 비동기 스레드로 Slack 웹훅 전송 (메인 루프 블로킹 방지)
            def send():
                try:
                    requests.post(self.webhook_url, json=payload, timeout=5)
                except Exception:
                    pass
            threading.Thread(target=send, daemon=True).start()
        except Exception:
            pass

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
        
        # Slack Webhook 연동 핸들러 추가
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            slack_handler = SlackAlertHandler(webhook_url)
            slack_handler.setFormatter(formatter)
            logger.addHandler(slack_handler)
    
    return logger


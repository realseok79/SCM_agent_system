# utils/logger.py
import logging, os, threading, re, json
from dotenv import load_dotenv
load_dotenv()

# Regex pattern covering common emojis, symbols, and pictographs
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff"  # Supplemental planes (most modern emojis)
    r"\u2600-\u27bf"          # Dingbats and miscellaneous symbols (e.g. ⚠️, ⚡)
    r"\u2300-\u23ff"          # Miscellaneous Technical
    r"\u2b50"                 # Medium white star
    r"\u3299"                 # Circled ideograph congratulation
    r"]+", 
    flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    if not isinstance(text, str):
        return text
    return EMOJI_PATTERN.sub("", text).strip()

class StructuredJsonFormatter(logging.Formatter):
    """
    [고도화 B6] 구조화된 로깅 (JSON)
    로그 메시지를 JSON 구조로 변경하여 ELK, Loki 등 로그 수집 시스템에 원활히 통합되도록 합니다.
    """
    def format(self, record):
        log_msg = record.msg
        if isinstance(log_msg, str):
            log_msg = strip_emojis(log_msg)
            
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "logger": record.name,
            "level": record.levelname,
            "message": log_msg
        }
        
        # Exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)

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
            # Send Slack webhook asynchronously to prevent blocking main loop
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

    # Prevent adding duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        # Use Structured JSON Formatter by default
        formatter = StructuredJsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Slack Webhook handler integration
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            slack_handler = SlackAlertHandler(webhook_url)
            slack_handler.setFormatter(formatter)
            logger.addHandler(slack_handler)
    
    return logger

# tests/test_logger_slack_alert.py
import logging
import os
import time
from unittest.mock import patch, MagicMock
from utils.logger import get_logger, SlackAlertHandler

def test_slack_alert_handler_attached(monkeypatch):
    """SLACK_WEBHOOK_URL이 설정된 경우 SlackAlertHandler가 로거에 장착되는지 검증"""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/webhook")
    
    # 새로운 이름의 로거 생성
    logger = get_logger("test_slack_attached")
    
    handlers = logger.handlers
    has_slack_handler = any(isinstance(h, SlackAlertHandler) for h in handlers)
    assert has_slack_handler is True

@patch("requests.post")
def test_slack_alert_handler_emits_on_error(mock_post, monkeypatch):
    """ERROR 등급 로그 발생 시 Slack 웹훅 POST 호출 검증 (비동기 수행 대응)"""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test/webhook")
    
    logger = get_logger("test_slack_emits")
    
    # ERROR 레벨 로그 출력
    logger.error("Test critical connection timeout occurred")
    
    # 비동기 스레드 실행 시간을 감안하여 약간의 대기
    time.sleep(0.5)
    
    # requests.post 가 호출되었는지 검증
    assert mock_post.called
    args, kwargs = mock_post.call_args
    assert args[0] == "https://hooks.slack.com/services/test/webhook"
    assert "Test critical connection timeout occurred" in kwargs["json"]["text"]

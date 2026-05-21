# tests/test_iot_agent.py
import pytest
from unittest.mock import patch, MagicMock
from agents.iot_agent import run_iot_sensor_cycle

@patch("agents.iot_agent.requests.get")
@patch("agents.iot_agent.requests.post")
def test_run_iot_sensor_cycle_success(mock_post, mock_get):
    # Mock ACTIVE devices response
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = [
        {"deviceId": "SENS-TEMP-001", "sensorType": "temperature", "regionCode": "KR-11", "status": "ACTIVE"},
        {"deviceId": "SENS-HUMI-001", "sensorType": "humidity", "regionCode": "KR-26", "status": "ACTIVE"}
    ]
    mock_get.return_value = mock_get_response

    # Mock POST telemetry response
    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    mock_post.return_value = mock_post_response

    # Run the cycle
    run_iot_sensor_cycle()

    # Verify requests were made correctly
    mock_get.assert_called_once()
    mock_post.assert_called_once()
    
    # Check that post was called with appropriate json data
    args, kwargs = mock_post.call_args
    posted_json = kwargs.get("json", [])
    assert len(posted_json) == 2
    assert posted_json[0]["deviceId"] == "SENS-TEMP-001"
    assert "value" in posted_json[0]
    assert posted_json[1]["deviceId"] == "SENS-HUMI-001"
    assert "value" in posted_json[1]

@patch("agents.iot_agent.requests.get")
def test_run_iot_sensor_cycle_no_devices(mock_get):
    # Mock empty response
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = []
    mock_get.return_value = mock_get_response

    with patch("agents.iot_agent.requests.post") as mock_post:
        run_iot_sensor_cycle()
        mock_post.assert_not_called()

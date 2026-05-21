# agents/iot_agent.py
import os
import requests
from utils.logger import get_logger
from utils.connectors.iot_simulator import IoTSensorSimulator

logger = get_logger("IoT_Agent")
simulator = IoTSensorSimulator()

def run_iot_sensor_cycle():
    """
    1. 서버에서 ACTIVE 디바이스만 조회
    2. 등록된 디바이스에 대해서만 센서값 생성 (시뮬레이션)
    3. 중앙 서버로 전송
    """
    api_base = os.getenv("MOCK_API_HOST", "http://localhost:8080")
    devices_url = f"{api_base}/api/iot/devices?status=ACTIVE"
    telemetry_url = f"{api_base}/api/iot/telemetry"

    try:
        # 1. ACTIVE 디바이스 조회
        res = requests.get(devices_url, timeout=5)
        if res.status_code != 200:
            logger.error(f"❌ Failed to fetch active IoT devices: HTTP {res.status_code}")
            return
        
        active_devices = res.json()
        if not active_devices:
            pass # logger.debug("💡 No active IoT devices registered.")
            return

        # 2. 센서값 생성
        telemetry_payload = []
        for device in active_devices:
            device_id = device.get("deviceId")
            sensor_type = device.get("sensorType")
            region_code = device.get("regionCode")
            
            # Use the lowpass EMA filter from iot_simulator
            val = simulator.get_filtered_reading(region_code, sensor_type)
            
            telemetry_payload.append({
                "deviceId": device_id,
                "value": round(val, 2)
            })

        # 3. 중앙 서버로 전송
        post_res = requests.post(telemetry_url, json=telemetry_payload, timeout=5)
        if post_res.status_code == 200:
            logger.info(f"✅ Ingested telemetry for {len(telemetry_payload)} active devices.")
        else:
            logger.error(f"❌ Telemetry ingestion failed: HTTP {post_res.status_code} - {post_res.text}")

    except Exception as e:
        logger.error(f"❌ IoT Sensor Cycle Error: {e}")

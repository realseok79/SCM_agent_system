FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성 (matplotlib용 폰트)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# 소스 코드 복사
COPY scm-agent-system/ ./scm-agent-system/


WORKDIR /app/scm-agent-system

EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]

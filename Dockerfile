# Python FastAPI Application for Keywords500 Dashboard
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (psycopg2-binary용)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 (Coolify에서 오버라이드 가능)
ENV DB_HOST=192.168.1.148
ENV DB_NAME=postgres
ENV DB_USER=postgres
ENV DB_PORT=5432

# 포트 설정
EXPOSE 8500

# 애플리케이션 실행
CMD ["uvicorn", "dashboard:app", "--host", "0.0.0.0", "--port", "8500"]

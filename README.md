# Keywords500 대시보드

쇼핑 플랫폼의 인기 검색어 500개를 자동으로 수집하고 시각화하는 웹 대시보드 애플리케이션입니다.

## 주요 기능

- 쇼핑몰 인기 검색어 500개 자동 수집
- 날짜별 키워드 데이터 조회 및 시각화
- CSV 백업 기능
- 웹 기반 대시보드 인터페이스
- 수집 작업 관리 (시작/중지)

## 기술 스택

- **백엔드**: Python, FastAPI
- **프론트엔드**: HTML, CSS, JavaScript, Bootstrap 5
- **데이터베이스**: PostgreSQL
- **배포**: Systemd 서비스

## 설치 및 실행 방법

### 필수 요구사항

- Python 3.8+
- PostgreSQL
- Chrome WebDriver

### 설치

1. 저장소 클론
   ```bash
   git clone https://github.com/yourusername/keywords500.git
   cd keywords500
   ```

2. 가상환경 생성 및 활성화
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   ```

3. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정
   ```
   DB_HOST=localhost
   DB_NAME=yourdbname
   DB_USER=youruser
   DB_PASSWORD=yourpassword
   DB_PORT=5432
   ```

### 실행

개발 모드로 실행:
```bash
uvicorn dashboard:app --host 0.0.0.0 --port 8000 --reload
```

서비스로 실행:
```bash
sudo systemctl start keywords500.service
```

## systemd 서비스 관리

서비스 관리 명령어:
```bash
# 서비스 시작
sudo systemctl start keywords500.service

# 서비스 상태 확인
sudo systemctl status keywords500.service

# 로그 확인
sudo journalctl -u keywords500.service -f
```

## 프로젝트 구조

- `dashboard.py`: 웹 대시보드 애플리케이션 (FastAPI)
- `scrape_keywords.py`: 키워드 수집 스크립트
- `templates/`: HTML 템플릿
- `static/`: JavaScript, CSS 파일
- `csv_backups/`: CSV 백업 파일 저장소

## 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 LICENSE 파일을 참조하세요. 
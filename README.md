# Keywords500 - 쇼핑 트렌드 분석 시스템

네이버 데이터랩 쇼핑인사이트에서 인기 검색어 TOP 500을 자동으로 수집하고, 트렌드를 분석하여 미래 상품 수요를 예측하는 시스템입니다.

## 🎯 프로젝트 목적

### 핵심 목표
1. **트렌드 파악**: 어떤 상품이 현재 유행하고 있는지 실시간으로 파악
2. **하락 감지**: 인기가 점점 떨어지는 상품을 조기에 감지
3. **수요 예측**: 과거 데이터를 기반으로 미래에 인기 있을 상품을 예측

### 활용 분야
- 이커머스 상품 기획 및 재고 관리
- 마케팅 전략 수립
- 시즌별 트렌드 분석
- 신규 상품 발굴

## 📊 데이터 현황

| 항목 | 내용 |
|------|------|
| **데이터 소스** | 네이버 데이터랩 쇼핑인사이트 |
| **수집 카테고리** | 패션의류 > 남성의류 |
| **수집 주기** | 매일 오전 8시 자동 수집 |
| **수집 기간** | 2020-03-30 ~ 현재 (약 1,900일+) |
| **일별 키워드** | 500개 |
| **저장소** | PostgreSQL 데이터베이스 + CSV 백업 |

## 🚀 향후 개발 계획

### Phase 1: 데이터 분석 기능 (예정)
- [ ] 키워드 순위 변동 추적 (상승/하락 트렌드)
- [ ] 신규 진입 키워드 알림
- [ ] 순위권 이탈 키워드 감지
- [ ] 주간/월간 트렌드 리포트 생성

### Phase 2: 시각화 고도화 (예정)
- [ ] 키워드별 순위 변동 차트
- [ ] 시계열 트렌드 그래프
- [ ] 카테고리별 인기도 히트맵
- [ ] 대시보드 실시간 업데이트

### Phase 3: 예측 모델 개발 (예정)
- [ ] 시계열 분석 (ARIMA, Prophet)
- [ ] 머신러닝 기반 트렌드 예측
- [ ] 계절성 패턴 분석
- [ ] 이상치 탐지 (급상승/급하락 키워드)

### Phase 4: 확장 기능 (예정)
- [ ] 다중 카테고리 수집 (여성의류, 가전 등)
- [ ] 알림 시스템 (이메일, 슬랙)
- [ ] API 제공 (외부 시스템 연동)
- [ ] 경쟁사 키워드 비교 분석

## 🛠 기술 스택

| 구분 | 기술 |
|------|------|
| **백엔드** | Python, FastAPI |
| **프론트엔드** | HTML, CSS, JavaScript, Bootstrap 5 |
| **데이터베이스** | PostgreSQL |
| **스크래핑** | Selenium, BeautifulSoup |
| **배포** | Systemd 서비스 |
| **스케줄링** | Cron |

## 📁 프로젝트 구조

```
keywords500/
├── dashboard.py          # 웹 대시보드 (FastAPI)
├── scrape_keywords.py    # 키워드 수집 스크립트
├── templates/            # HTML 템플릿
│   └── index.html
├── static/               # 정적 파일
│   ├── script.js
│   └── style.css
├── csv_backups/          # CSV 백업 파일
├── keywords500.service   # Systemd 서비스 파일
├── requirements.txt      # Python 의존성
└── README.md
```

## ⚙️ 설치 및 실행

### 필수 요구사항
- Python 3.8+
- PostgreSQL
- Chrome 브라우저 (스크래핑용)

### 설치

1. **저장소 클론**
   ```bash
   git clone https://github.com/kks0488/keywords500.git
   cd keywords500
   ```

2. **가상환경 생성 및 활성화**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   ```

3. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

4. **환경 변수 설정**
   ```bash
   export DB_HOST=localhost
   export DB_NAME=postgres
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   export DB_PORT=5432
   ```

### 실행

**개발 모드:**
```bash
uvicorn dashboard:app --host 0.0.0.0 --port 8500 --reload
```

**서비스 모드:**
```bash
sudo systemctl start keywords500.service
```

**수동 스크래핑:**
```bash
# 전전날 데이터 수집 (기본)
python scrape_keywords.py

# 특정 날짜 수집
python scrape_keywords.py --start-date 2025-01-01

# 기간 지정 수집
python scrape_keywords.py --start-date 2025-01-01 --end-date 2025-01-31
```

## 🔧 서비스 관리

### Systemd 명령어
```bash
# 서비스 시작
sudo systemctl start keywords500.service

# 서비스 중지
sudo systemctl stop keywords500.service

# 서비스 재시작
sudo systemctl restart keywords500.service

# 서비스 상태 확인
sudo systemctl status keywords500.service

# 로그 확인
sudo journalctl -u keywords500.service -f
```

### Cron 스케줄
```bash
# 현재 스케줄 확인
crontab -l

# 매일 오전 8시 자동 수집
0 8 * * * cd /home/kkaemo/projects/keywords500 && .venv/bin/python scrape_keywords.py >> cron.log 2>&1
```

## 📈 대시보드 접속

- **URL**: `http://서버IP:8500`
- **기능**:
  - 실시간 스크래핑 상태 확인
  - 날짜별 키워드 조회
  - 실행 로그 모니터링
  - 수동 스크래핑 실행/중지

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👤 작성자

- GitHub: [@kks0488](https://github.com/kks0488)

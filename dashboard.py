import os
import datetime
import subprocess
import psutil
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import DictCursor

# --- 설정 ---
# 데이터베이스 접속 정보 (환경 변수 사용 권장)
DB_HOST = os.environ.get("DB_HOST", "192.168.1.148")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Wldms1701!!")
DB_PORT = os.environ.get("DB_PORT", "5432")

# 스크래핑 스크립트 경로 (Docker: /app, Local: /home/kkaemo/projects/keywords500)
APP_BASE_PATH = os.environ.get("APP_BASE_PATH", "/app")
SCRAPE_SCRIPT_PATH = os.path.join(APP_BASE_PATH, "scrape_keywords.py")
PYTHON_EXECUTABLE_PATH = os.environ.get("PYTHON_EXECUTABLE", "python")  # Docker에서는 시스템 Python 사용

# 로그 파일 경로
LOG_FILE_PATH = os.path.join(APP_BASE_PATH, "scrape_run.log")

# FastAPI 앱 설정
app = FastAPI(title="Keyword Dashboard")

# --- Pydantic 모델 정의 ---
class ScrapeRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- 데이터베이스 연결 함수 ---
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

# --- 헬퍼 함수: 스크립트 프로세스 찾기 ---
def find_scrape_process():
    """실행 중인 scrape_keywords.py 프로세스를 찾아 PID를 반환합니다."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # 프로세스 커맨드 라인에 스크립트 경로가 포함되어 있는지 확인
            cmdline = proc.info.get('cmdline', [])
            if cmdline and isinstance(cmdline, list) and SCRAPE_SCRIPT_PATH in cmdline:
                return proc.info['pid']  # PID 반환
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None  # 프로세스를 찾지 못하면 None 반환

# --- API 엔드포인트 ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """메인 대시보드 페이지를 렌더링합니다."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/dates", response_class=JSONResponse)
async def get_available_dates():
    """데이터베이스에서 데이터가 있는 날짜 목록을 조회합니다."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT scrape_date FROM daily_keywords ORDER BY scrape_date DESC;")
        dates = [row[0].strftime('%Y-%m-%d') for row in cur.fetchall()]
        cur.close()
        return {"dates": dates}
    except Exception as e:
        print(f"Error fetching dates: {e}")
        raise HTTPException(status_code=500, detail="날짜 목록 조회 중 오류 발생")
    finally:
        if conn:
            conn.close()

@app.get("/api/keywords/{date_str}", response_class=JSONResponse)
async def get_keywords_by_date(date_str: str):
    """지정된 날짜의 키워드 목록을 조회합니다."""
    conn = None
    try:
        # 날짜 형식 검증
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")

        conn = get_db_connection()
        # DictCursor를 사용하여 결과를 딕셔너리로 받음
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute(
            "SELECT keyword_rank, keyword FROM daily_keywords WHERE scrape_date = %s ORDER BY keyword_rank;",
            (target_date,)
        )
        keywords = cur.fetchall()
        cur.close()
        # 결과를 JSON 직렬화 가능한 형태로 변환
        keywords_list = [{"rank": row["keyword_rank"], "keyword": row["keyword"]} for row in keywords]
        return {"keywords": keywords_list}
    except HTTPException as http_exc: # 이미 발생한 HTTP 예외는 그대로 전달
        raise http_exc
    except Exception as e:
        print(f"Error fetching keywords for {date_str}: {e}")
        raise HTTPException(status_code=500, detail="키워드 조회 중 오류 발생")
    finally:
        if conn:
            conn.close()

@app.get("/api/status", response_class=JSONResponse)
async def get_scrape_status():
    """스크래핑 스크립트 실행 상태와 PID를 확인합니다."""
    pid = find_scrape_process()
    return {"is_running": pid is not None, "pid": pid}

@app.post("/api/run-scrape", response_class=JSONResponse)
async def run_scrape_script(scrape_request: ScrapeRequest):
    """스크래핑 스크립트를 백그라운드로 실행합니다."""
    try:
        # 이미 실행 중인지 확인
        status = await get_scrape_status()
        if status.get("is_running"):
            raise HTTPException(status_code=409, detail="스크립트가 이미 실행 중입니다.")

        # 스크립트 파일 존재 확인
        if not os.path.exists(SCRAPE_SCRIPT_PATH):
            raise HTTPException(status_code=500, detail=f"스크립트 파일을 찾을 수 없습니다: {SCRAPE_SCRIPT_PATH}")

        # Python 실행 파일 존재 확인
        if not os.path.exists(PYTHON_EXECUTABLE_PATH):
            raise HTTPException(status_code=500, detail=f"Python 실행 파일을 찾을 수 없습니다: {PYTHON_EXECUTABLE_PATH}")

        cmd = [PYTHON_EXECUTABLE_PATH, SCRAPE_SCRIPT_PATH]
        if scrape_request.start_date:
            cmd.extend(["--start-date", scrape_request.start_date])
        if scrape_request.end_date:
            cmd.extend(["--end-date", scrape_request.end_date])

        print(f"Executing command: {' '.join(cmd)}")
        # 백그라운드에서 스크립트 실행
        process = subprocess.Popen(cmd)
        print(f"스크립트 프로세스 시작됨 (PID: {process.pid})")
        return {"message": "스크립트 실행을 시작했습니다.", "command": " ".join(cmd), "pid": process.pid}
    except HTTPException as http_exc:
        print(f"HTTP 오류 발생: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Error running scrape script: {e}")
        raise HTTPException(status_code=500, detail=f"스크립트 실행 중 오류 발생: {str(e)}")

@app.post("/api/stop-scrape", response_class=JSONResponse)
async def stop_scrape_script():
    """실행 중인 스크래핑 스크립트를 중지합니다."""
    print("스크립트 중지 API 호출됨") # 로그 추가
    pid = find_scrape_process()
    print(f"찾은 프로세스 PID: {pid}") # 로그 추가
    
    if pid is None:
        print("실행 중인 스크립트 없음") # 로그 추가
        raise HTTPException(status_code=404, detail="실행 중인 스크립트를 찾을 수 없습니다.")
    
    try:
        process = psutil.Process(pid)
        print(f"프로세스(PID: {pid}) 종료 시도...") # 로그 추가
        process.terminate() # SIGTERM 전송 (대부분의 OS에서 작동)
        print(f"스크립트 프로세스(PID: {pid})에 종료 신호(SIGTERM)를 보냈습니다.")
        return {"message": f"스크립트(PID: {pid})에 중지 신호를 보냈습니다. 잠시 후 상태를 확인하세요."}
    
    except psutil.NoSuchProcess:
        print(f"프로세스(PID: {pid})를 찾을 수 없음 (이미 종료됨?)") # 로그 추가
        raise HTTPException(status_code=404, detail="프로세스가 이미 종료되었거나 찾을 수 없습니다.")
    except Exception as e:
        print(f"스크립트(PID: {pid}) 중지 중 오류 발생: {e}") # 로그 추가
        raise HTTPException(status_code=500, detail=f"스크립트 중지 중 오류 발생: {e}")

@app.get("/api/logs", response_class=JSONResponse)
async def get_latest_logs(lines: int = 100):
    """로그 파일의 최신 내용을 지정된 줄 수만큼 반환합니다."""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            return {"logs": "로그 파일이 아직 생성되지 않았습니다."}

        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            # 파일의 마지막 N 라인을 효율적으로 읽기 (큰 파일 고려)
            log_lines = f.readlines()
            # 최신 로그가 아래에 추가되므로 마지막 N 라인을 가져옴
            latest_logs = log_lines[-lines:] 
        
        # 리스트를 하나의 문자열로 합침 (개행 유지)
        log_content = "".join(latest_logs)
        return {"logs": log_content}
    except Exception as e:
        print(f"Error reading log file: {e}")
        raise HTTPException(status_code=500, detail="로그 파일 읽기 중 오류 발생")

# --- Uvicorn 실행 (개발용) ---
# 터미널에서 직접 실행: uvicorn dashboard:app --reload
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000) 
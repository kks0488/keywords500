#!/usr/bin/env python
# coding: utf-8

import time
import datetime
import argparse  # 명령줄 인자 처리를 위해 추가
import sys       # 오류 발생 시 종료를 위해 추가
import os        # 환경 변수 사용을 위해 추가
import csv       # CSV 파일 처리를 위해 추가
import logging   # 로깅 모듈 임포트
import psycopg2 # PostgreSQL 연동을 위해 추가
from psycopg2.extras import execute_values # 대량 INSERT를 위해 추가
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- 설정 ---
TARGET_URL = "https://datalab.naver.com/shoppingInsight/sCategory.naver"
INTER_DATE_SLEEP_SECONDS = 10 # 각 날짜 처리 사이 대기 시간 (초)

# --- PostgreSQL 접속 정보 ---
# 환경 변수에서 읽거나 기본값 사용
DB_HOST = os.environ.get("DB_HOST", "192.168.1.148")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Wldms1701!!")
DB_PORT = os.environ.get("DB_PORT", "5432")

# --- CSS 선택자 (사용자 제공 HTML 기반, 필요시 실제 사이트에서 F12로 재확인) ---
# 카테고리
CATEGORY_1ST_BTN_SELECTOR = "div.set_period.category > div.select:nth-of-type(1) > span.select_btn"
FASHION_CLOTHING_OPTION_SELECTOR = "div.set_period.category > div.select:nth-of-type(1) ul.select_list a.option[data-cid='50000000']"
CATEGORY_2ND_BTN_SELECTOR = "div.set_period.category > div.select:nth-of-type(2) > span.select_btn"
MENS_CLOTHING_OPTION_SELECTOR = "div.set_period.category > div.select:nth-of-type(2) ul.select_list a.option[data-cid='50000169']"

# 기간
TIMEFRAME_BTN_SELECTOR = "div.set_period > div.select.w4 > span.select_btn"
DAILY_OPTION_SELECTOR = "div.set_period > div.select.w4 ul.select_list a.option" # '일간' 텍스트 포함 확인 필요

# 날짜 (시작일과 종료일 선택기 - 구조가 유사하다고 가정)
# 예시: 시작일 연도 버튼 -> div.set_period_target > span:nth-of-type(1) > div.select.w2 > span.select_btn
# 예시: 시작일 연도 옵션 -> div.set_period_target > span:nth-of-type(1) > div.select.w2 ul.select_list a.option[text='{}']
# 날짜 선택기는 구조가 복잡하므로, 실제 구현 시 정확한 선택자 필요 (시작/종료, 연/월/일)
# 여기서는 단순화를 위해 JavaScript로 직접 날짜를 설정하는 방식을 고려해볼 수 있음 (선택: 고급)

# 연령
AGE_CHECKBOX_SELECTOR_TEMPLATE = "input[type='checkbox'][value='{}']" # value는 20, 30 등 숫자 문자열
AGES_TO_SELECT = ['20', '30', '40', '50', '60']

# 조회 버튼
SEARCH_BUTTON_SELECTOR = "a.btn_submit" # 이전 코드 기반, 확인 필요

# 결과 목록 및 페이지네이션
KEYWORD_LIST_CONTAINER_SELECTOR = "ul.rank_top1000_list"
KEYWORD_ITEM_SELECTOR = "li a.link_text" # 키워드 텍스트 포함 링크
RANK_NUM_SELECTOR = "span.rank_top1000_num" # 순위 숫자 포함 span
NEXT_PAGE_BTN_SELECTOR = "a.btn_page_next"
PAGE_INFO_SELECTOR = "span.page_info" # 예: "1 /25"

# --- 백업 디렉토리 --- 
BACKUP_DIR = "csv_backups"
LOG_FILE = "scrape_run.log" # 로그 파일명 정의

# --- 로거 설정 --- (스크립트 실행 시 한 번만 설정되도록)
def setup_logging():
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 파일 핸들러
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 (기존 print처럼 터미널에도 보이게)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)

# --- 함수 정의 ---

def setup_driver():
    """Selenium WebDriver 설정"""
    logger = logging.getLogger() # 함수 내에서 로거 가져오기
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized") # 창 최대화 (헤드리스에서는 큰 의미 없을 수 있음)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("WebDriver 설정 완료.")
        return driver
    except Exception as e:
        logger.error(f"WebDriver 설정 중 오류 발생: {e}")
        return None

def click_element(driver, selector, wait_time=10):
    """요소 클릭 (WebDriverWait 사용)"""
    logger = logging.getLogger()
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        element.click()
        time.sleep(0.5) # 클릭 후 잠시 대기
        return True
    except TimeoutException:
        logger.error(f"오류: 요소를 찾거나 클릭할 수 없습니다 (시간 초과): {selector}")
        return False
    except ElementClickInterceptedException:
         logger.warning(f"오류: 요소 클릭이 가로막혔습니다: {selector}. JavaScript 클릭 시도...")
         try:
             element = driver.find_element(By.CSS_SELECTOR, selector)
             driver.execute_script("arguments[0].click();", element)
             time.sleep(0.5)
             return True
         except Exception as e_js:
             logger.error(f"오류: JavaScript 클릭 실패: {e_js}")
             return False
    except Exception as e:
        logger.error(f"오류: 요소 클릭 중 예상치 못한 오류: {selector} - {e}")
        return False

def select_date_via_js(driver, year, month, day):
    """ JavaScript를 사용하여 날짜 설정 (주의: 사이트 구조에 따라 동작 안 할 수 있음) """
    logger = logging.getLogger()
    logger.warning("경고: JavaScript를 이용한 날짜 설정은 불안정할 수 있습니다.")
    try:
        # 예시: 특정 input 필드에 날짜 값을 직접 설정하는 방식 (해당 input 필드의 ID나 name 필요)
        # driver.execute_script(f"document.getElementById('startDateInputId').value = '{year}-{month:02d}-{day:02d}';")
        # driver.execute_script(f"document.getElementById('endDateInputId').value = '{year}-{month:02d}-{day:02d}';")
        # 날짜 변경 후 관련 이벤트(예: change)를 트리거해야 할 수도 있습니다.
        logger.info(f"JavaScript로 날짜 설정을 시도했습니다: {year}-{month:02d}-{day:02d}. (성공 보장 없음)")
        return True
    except Exception as e:
        logger.error(f"JavaScript 날짜 설정 중 오류: {e}")
        return False

def select_date_via_ui(driver, year, month, day):
    """ UI 클릭을 통해 날짜 설정 (시작일/종료일 모두 동일하게 설정) - 플랜 A/B 적용 """
    logger = logging.getLogger()
    logger.info(f"날짜 선택 시작 (플랜 A/B): {year}-{month:02d}-{day:02d}")
    year_str = str(year)
    month_str = f"{month:02d}"
    day_str = f"{day:02d}"

    # --- 선택자 정의 ---
    # 시작일
    start_date_base_selector = "div.set_period_target > span:nth-of-type(1)"
    start_year_btn_selector = f"{start_date_base_selector} > div.select.w2 > span.select_btn"
    start_year_options_selector = f"{start_date_base_selector} > div.select.w2 ul.select_list a.option"
    start_month_btn_selector = f"{start_date_base_selector} > div.select.w3:nth-of-type(2) > span.select_btn"
    start_month_options_selector = f"{start_date_base_selector} > div.select.w3:nth-of-type(2) ul.select_list a.option"
    start_day_btn_selector = f"{start_date_base_selector} > div.select.w3:nth-of-type(3) > span.select_btn"
    start_day_options_selector = f"{start_date_base_selector} > div.select.w3:nth-of-type(3) ul.select_list a.option"
    # 종료일
    end_date_base_selector = "div.set_period_target > span:nth-of-type(3)"
    end_year_btn_selector = f"{end_date_base_selector} > div.select.w2 > span.select_btn"
    end_year_options_selector = f"{end_date_base_selector} > div.select.w2 ul.select_list a.option"
    end_month_btn_selector = f"{end_date_base_selector} > div.select.w3:nth-of-type(2) > span.select_btn"
    end_month_options_selector = f"{end_date_base_selector} > div.select.w3:nth-of-type(2) ul.select_list a.option"
    end_day_btn_selector = f"{end_date_base_selector} > div.select.w3:nth-of-type(3) > span.select_btn"
    end_day_options_selector = f"{end_date_base_selector} > div.select.w3:nth-of-type(3) ul.select_list a.option"

    def click_option_by_text(driver, button_selector, options_selector, text_to_find):
        """ 버튼을 클릭하고, 드롭다운에서 텍스트가 일치하는 옵션을 찾아 클릭 (안정성 강화) """
        try:
            # 1. 버튼 클릭하여 드롭다운 열기
            if not click_element(driver, button_selector): return False
            # time.sleep(0.3) # 단순 대기 대신 명시적 대기 사용

            # 2. 옵션 목록(ul)이 나타날 때까지 대기
            list_selector_parts = options_selector.split(' a.option')
            if len(list_selector_parts) == 2 and list_selector_parts[1] == '':
                list_selector = list_selector_parts[0]
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, list_selector))
                    )
                    time.sleep(0.2) # 목록 나타난 후 짧은 대기
                except TimeoutException:
                    logger.warning(f"오류: 옵션 목록({list_selector})이 시간 내에 나타나지 않습니다.")
                    # 드롭다운을 닫기 위해 body 클릭 시도 (선택적)
                    try: driver.find_element(By.TAG_NAME, 'body').click()
                    except: pass
                    return False
            else:
                logger.warning(f"경고: 옵션 목록 선택자 구조가 예상과 다릅니다: {options_selector}. 이전 방식대로 진행합니다.")
                time.sleep(0.3) # 폴백으로 단순 대기

            # 3. 옵션 목록 찾기 및 클릭
            options = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, options_selector))
            )
            found = False
            for option in options:
                # 옵션 텍스트 비교 전에 요소가 유효한지 확인 (StaleElement 예방)
                try:
                    option_text = option.text.strip()
                except EC.StaleElementReferenceException:
                    logger.warning("    경고: 옵션 요소가 Stale 상태가 됨. 목록 재탐색 시도...")
                    # 목록을 다시 찾아 현재 옵션 인덱스에 해당하는 새 요소 사용 (복잡도 증가)
                    # 여기서는 단순하게 다음 옵션으로 넘어감
                    continue 
                
                if option_text == text_to_find:
                    try:
                        # 4. 클릭 전 스크롤하여 보이도록 함
                        driver.execute_script("arguments[0].scrollIntoView(true);", option)
                        time.sleep(0.2) # 스크롤 후 짧은 대기

                        # 5. 클릭 가능한 상태가 될 때까지 기다렸다가 클릭
                        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(option))
                        option.click()
                        found = True
                        logger.info(f"  - '{text_to_find}' 선택 완료.")
                        time.sleep(0.5) # 클릭 후 UI 반영 대기
                        break
                    except ElementClickInterceptedException:
                        logger.warning(f"    경고: '{text_to_find}' 옵션 클릭 가로막힘. JS 클릭 시도...")
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", option) # JS 클릭 전에도 스크롤
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", option)
                            found = True
                            logger.info(f"  - '{text_to_find}' JS 클릭 완료.")
                            time.sleep(0.5)
                            break
                        except Exception as e_js_click:
                            logger.error(f"    오류: '{text_to_find}' JS 클릭 중 오류: {e_js_click}")
                            return False # JS 클릭도 실패하면 중단
                    except EC.StaleElementReferenceException:
                         logger.warning(f"    오류: 클릭하려는 '{text_to_find}' 옵션 요소가 Stale 상태가 됨.")
                         # 이 경우 재시도 로직이 필요할 수 있으나, 우선 실패 처리
                         return False
                    except Exception as e_click:
                         logger.error(f"    오류: '{text_to_find}' 옵션 클릭 중 예상치 못한 오류: {e_click}")
                         return False # 옵션 클릭 실패 시 중단
            
            if not found:
                 logger.error(f"    오류: '{text_to_find}' 옵션을 찾을 수 없습니다. (선택자: {options_selector})")
                 return False
            return True

        except TimeoutException:
            logger.error(f"오류: 시간 초과 - 버튼({button_selector}) 또는 옵션({options_selector})을 찾을 수 없습니다.")
            return False
        except Exception as e:
            logger.error(f"오류: 날짜 옵션 '{text_to_find}' 선택 중 예상치 못한 오류: {e}")
            return False

    # --- 플랜 A 시도: 종료일 -> 시작일 --- 
    logger.info("--- 날짜 선택 플랜 A 시도 (종료일 -> 시작일) ---")
    plan_a_success = False
    try:
        logger.info("  --- 종료일 설정 (플랜 A) ---")
        if not click_option_by_text(driver, end_year_btn_selector, end_year_options_selector, year_str): raise ValueError("Plan A Failed")
        if not click_option_by_text(driver, end_month_btn_selector, end_month_options_selector, month_str): raise ValueError("Plan A Failed")
        if not click_option_by_text(driver, end_day_btn_selector, end_day_options_selector, day_str): raise ValueError("Plan A Failed")
        logger.info("  --- 종료일 설정 완료 (플랜 A) ---")
        time.sleep(0.5)
        logger.info("  --- 시작일 설정 (플랜 A) ---")
        if not click_option_by_text(driver, start_year_btn_selector, start_year_options_selector, year_str): raise ValueError("Plan A Failed")
        if not click_option_by_text(driver, start_month_btn_selector, start_month_options_selector, month_str): raise ValueError("Plan A Failed")
        if not click_option_by_text(driver, start_day_btn_selector, start_day_options_selector, day_str): raise ValueError("Plan A Failed")
        logger.info("  --- 시작일 설정 완료 (플랜 A) ---")
        plan_a_success = True
        logger.info("--- 날짜 선택 플랜 A 성공 ---")
    except Exception as e_a:
        logger.warning(f"--- 날짜 선택 플랜 A 실패: {e_a} ---")

    if plan_a_success:
        logger.info(f"날짜 선택 최종 완료 (플랜 A): {year}-{month_str}-{day_str}")
        return True
    else:
        # --- 플랜 B 시도: 시작일 -> 종료일 --- 
        logger.info("--- 날짜 선택 플랜 B 시도 (시작일 -> 종료일) ---")
        plan_b_success = False
        try:
            logger.info("  --- 시작일 설정 (플랜 B) ---")
            if not click_option_by_text(driver, start_year_btn_selector, start_year_options_selector, year_str): raise ValueError("Plan B Failed")
            if not click_option_by_text(driver, start_month_btn_selector, start_month_options_selector, month_str): raise ValueError("Plan B Failed")
            if not click_option_by_text(driver, start_day_btn_selector, start_day_options_selector, day_str): raise ValueError("Plan B Failed")
            logger.info("  --- 시작일 설정 완료 (플랜 B) ---")
            time.sleep(0.5)
            logger.info("  --- 종료일 설정 (플랜 B) ---")
            if not click_option_by_text(driver, end_year_btn_selector, end_year_options_selector, year_str): raise ValueError("Plan B Failed")
            if not click_option_by_text(driver, end_month_btn_selector, end_month_options_selector, month_str): raise ValueError("Plan B Failed")
            if not click_option_by_text(driver, end_day_btn_selector, end_day_options_selector, day_str): raise ValueError("Plan B Failed")
            logger.info("  --- 종료일 설정 완료 (플랜 B) ---")
            plan_b_success = True
            logger.info("--- 날짜 선택 플랜 B 성공 ---")
        except Exception as e_b:
            logger.warning(f"--- 날짜 선택 플랜 B 실패: {e_b} ---")

        if plan_b_success:
            logger.info(f"날짜 선택 최종 완료 (플랜 B): {year}-{month_str}-{day_str}")
            return True
        else:
            logger.error(f"오류: 날짜 선택 플랜 A, B 모두 실패 ({year}-{month_str}-{day_str})")
            return False

def save_to_csv(keywords_data, scrape_date_str):
    """수집된 데이터를 CSV 파일로 백업 저장"""
    logger = logging.getLogger()
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        filename = f"backup_{scrape_date_str}.csv"
        filepath = os.path.join(BACKUP_DIR, filename)
        logger.info(f"CSV 백업 시도: {filepath}")

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            csvwriter = csv.writer(csvfile)
            # 헤더 작성
            csvwriter.writerow(['rank', 'keyword'])
            # 데이터 작성
            for rank, keyword in enumerate(keywords_data):
                csvwriter.writerow([rank + 1, keyword])
        
        logger.info(f"CSV 백업 완료: {filepath}")
        return True
    except Exception as e:
        logger.error(f"CSV 백업 중 오류 발생: {e}")
        return False

def scrape_page_keywords(driver):
    """현재 페이지의 키워드 목록 스크랩"""
    logger = logging.getLogger()
    keywords_on_page = []
    try:
        # 목록 컨테이너가 로드될 때까지 잠시 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, KEYWORD_LIST_CONTAINER_SELECTOR))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        keyword_container = soup.select_one(KEYWORD_LIST_CONTAINER_SELECTOR)
        if keyword_container:
            keyword_items = keyword_container.select(KEYWORD_ITEM_SELECTOR)
            for item in keyword_items:
                rank_span = item.select_one(RANK_NUM_SELECTOR)
                rank_text = rank_span.get_text(strip=True) if rank_span else ""
                # 키워드 텍스트 추출 (순위 숫자 제외)
                keyword_text = item.get_text(strip=True)
                if rank_text and keyword_text.startswith(rank_text):
                     # 순위 숫자가 맨 앞에 있으면 제거 (공백처리 포함)
                     keyword = keyword_text[len(rank_text):].strip()
                else:
                     keyword = keyword_text # 순위가 없거나 다른 형식인 경우 그대로 사용
                if keyword:
                     keywords_on_page.append(keyword)
    except Exception as e:
        logger.error(f"페이지 키워드 스크랩 중 오류: {e}")
    return keywords_on_page

def save_to_db(keywords_data, scrape_date_str):
    """수집된 데이터를 PostgreSQL에 저장"""
    logger = logging.getLogger()
    conn = None
    try:
        logger.info("데이터베이스 연결 시도...")
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        cur = conn.cursor()
        logger.info("데이터베이스 연결 성공.")
        logger.info(f"{scrape_date_str} 날짜의 기존 키워드 데이터 삭제 시도...")
        delete_sql = "DELETE FROM daily_keywords WHERE scrape_date = %s AND category_id = '50000169';"
        cur.execute(delete_sql, (scrape_date_str,))
        logger.info(f"삭제된 행 개수: {cur.rowcount}")
        insert_sql = """
            INSERT INTO daily_keywords (scrape_date, keyword_rank, keyword, category_id)
            VALUES %s
            ON CONFLICT (scrape_date, keyword_rank, category_id) DO NOTHING;
        """
        values_to_insert = [
            (scrape_date_str, rank + 1, keyword, '50000169')
            for rank, keyword in enumerate(keywords_data)
        ]
        if values_to_insert:
             logger.info(f"{len(values_to_insert)}개의 키워드 데이터베이스 저장 시도...")
             execute_values(cur, insert_sql, values_to_insert)
             conn.commit()
             logger.info("데이터베이스 저장 완료.")
        else:
             logger.info("저장할 키워드 데이터가 없습니다.")
        cur.close()
        return True # 성공 시 True 반환
    except psycopg2.Error as db_err:
        logger.error(f"데이터베이스 오류: {db_err}")
        if conn:
            conn.rollback() # 오류 발생 시 롤백
        return False # 실패 시 False 반환
    except Exception as e:
        logger.error(f"데이터 저장 중 예상치 못한 오류: {e}")
        if conn:
            conn.rollback() # 오류 발생 시 롤백
        return False # 실패 시 False 반환
    finally:
        if conn:
            conn.close()
            logger.info("데이터베이스 연결 종료.")

def scrape_single_date(driver, target_date):
    """지정된 날짜의 TOP 500 키워드를 스크랩하고 저장"""
    logger = logging.getLogger()
    logger.info(f"\n{'='*20} {target_date.strftime('%Y-%m-%d')} 데이터 수집 시작 {'='*20}")
    target_year = target_date.year
    target_month = target_date.month
    target_day = target_date.day
    scrape_date_str_for_db = target_date.strftime("%Y-%m-%d")
    all_keywords = []
    max_pages = 25

    try:
        # --- 페이지 초기화: 매번 URL 재접속 --- 
        logger.info(f"페이지 초기화 (재접속): {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(3) # 페이지 로딩 대기 (필요시 시간 조절)

        # --- 설정 적용 (카테고리, 기간 등은 한번만 해도 될 수 있으나, 안정성을 위해 매번 수행 고려) ---
        # 1. 카테고리 선택 (패션의류 > 남성의류)
        logger.info("카테고리 선택 중...")
        if not click_element(driver, CATEGORY_1ST_BTN_SELECTOR): raise Exception("패션의류 버튼 클릭 실패")
        if not click_element(driver, FASHION_CLOTHING_OPTION_SELECTOR): raise Exception("패션의류 옵션 클릭 실패")
        time.sleep(1)
        if not click_element(driver, CATEGORY_2ND_BTN_SELECTOR): raise Exception("2차 분류 버튼 클릭 실패")
        if not click_element(driver, MENS_CLOTHING_OPTION_SELECTOR): raise Exception("남성의류 옵션 클릭 실패")
        logger.info("카테고리 선택 완료.")
        time.sleep(1)

        # 2. 기간 '일간' 선택
        logger.info("기간 선택 중: 일간")
        if not click_element(driver, TIMEFRAME_BTN_SELECTOR): raise Exception("기간 버튼 클릭 실패")
        daily_options = driver.find_elements(By.CSS_SELECTOR, DAILY_OPTION_SELECTOR)
        daily_clicked = False
        for option in daily_options:
            if "일간" in option.text: option.click(); daily_clicked = True; logger.info("기간 '일간' 선택 완료."); time.sleep(0.5); break
        if not daily_clicked: raise Exception("기간 '일간' 옵션 클릭 실패")

        # 3. 날짜 선택
        logger.info("날짜 선택 시도...")
        if not select_date_via_ui(driver, target_year, target_month, target_day):
            raise Exception("날짜 선택 실패") # 날짜 선택 실패 시 해당 날짜 처리 중단
        time.sleep(1)

        # 4. 연령대 선택
        logger.info("연령대 선택 중...")
        for age in AGES_TO_SELECT:
            age_checkbox_selector = AGE_CHECKBOX_SELECTOR_TEMPLATE.format(age)
            checkbox = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, age_checkbox_selector)))
            if not checkbox.is_selected(): driver.execute_script("arguments[0].click();", checkbox); logger.info(f"- {age}대 선택"); time.sleep(0.2)
        logger.info("연령대 선택 완료.")

        # 5. 조회하기 버튼 클릭
        logger.info("조회하기 버튼 클릭 시도...")
        if not click_element(driver, SEARCH_BUTTON_SELECTOR): raise Exception("조회하기 버튼 클릭 실패")
        logger.info("조회 완료. 결과 로딩 대기...")
        time.sleep(3) # 결과 로딩 대기

        # 6. 페이지네이션하며 키워드 수집
        logger.info("키워드 수집 시작 (최대 25 페이지)...")
        current_page = 1
        while current_page <= max_pages:
            logger.info(f"- {current_page} 페이지 스크랩 중...")
            keywords_on_page = scrape_page_keywords(driver)
            if not keywords_on_page:
                 logger.warning(f"경고: {current_page} 페이지에서 키워드를 찾을 수 없습니다.")
                 # 필요시 재시도 로직 추가 가능

            all_keywords.extend(keywords_on_page)
            logger.info(f"  > {len(keywords_on_page)}개 수집 (총 {len(all_keywords)}개)")

            # 마지막 페이지 확인
            try:
                page_info = driver.find_element(By.CSS_SELECTOR, PAGE_INFO_SELECTOR).text
                if f"{current_page} / {max_pages}" in page_info.replace(" ", ""): logger.info("마지막 페이지 도달."); break
            except NoSuchElementException: logger.warning("페이지 정보 요소를 찾을 수 없음.")

            # 다음 페이지 버튼 클릭
            try:
                 next_button = driver.find_element(By.CSS_SELECTOR, NEXT_PAGE_BTN_SELECTOR)
                 if 'defult' in next_button.get_attribute('class'): logger.info("다음 페이지 버튼 비활성화됨 (마지막 페이지)."); break
                 logger.info("다음 페이지로 이동...")
                 driver.execute_script("arguments[0].click();", next_button)
                 time.sleep(2)
                 current_page += 1
            except NoSuchElementException: logger.warning("다음 페이지 버튼을 찾을 수 없음 (마지막 페이지일 수 있음)."); break
            except Exception as e_next: logger.error(f"다음 페이지 이동 중 오류: {e_next}"); break

        logger.info(f"\n총 {len(all_keywords)}개의 키워드 수집 완료 ({target_date.strftime('%Y-%m-%d')}).")

        # 6.5. CSV 파일로 백업 저장
        if all_keywords:
            if not save_to_csv(all_keywords, scrape_date_str_for_db):
                 logger.warning("경고: CSV 백업에 실패했습니다.")

        # 7. 데이터베이스에 저장
        if all_keywords:
            if not save_to_db(all_keywords, scrape_date_str_for_db):
                 logger.error(f"경고: 데이터베이스 저장에 실패했습니다 ({target_date.strftime('%Y-%m-%d')}).")
        else:
             logger.info("수집된 키워드가 없어 저장할 내용이 없습니다.")

        logger.info(f"{'='*20} {target_date.strftime('%Y-%m-%d')} 데이터 수집 완료 {'='*20}")
        return True # 성공 시 True 반환

    except Exception as e:
        logger.exception(f"오류: {target_date.strftime('%Y-%m-%d')} 데이터 처리 중 오류 발생: {e}") # logger.exception 사용
        # import traceback # 필요 없음
        # traceback.print_exc() # 필요 없음
        return False # 실패 시 False 반환


# --- 메인 실행 로직 --- 
if __name__ == "__main__":
    setup_logging() # 메인 시작 시 로깅 설정 호출
    logger = logging.getLogger() # 메인 로직용 로거 가져오기

    parser = argparse.ArgumentParser(description="네이버 데이터랩 쇼핑인사이트 키워드 스크래퍼 (기간별 수집 가능)")
    parser.add_argument("--start-date", help="수집 시작 날짜 (YYYY-MM-DD 형식)", default=None)
    parser.add_argument("--end-date", help="수집 종료 날짜 (YYYY-MM-DD 형식, 없으면 시작 날짜 하루만)", default=None)
    args = parser.parse_args()

    # 날짜 범위 결정
    dates_to_scrape = []
    try:
        if args.start_date:
            start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
            if args.end_date:
                end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
                if start_date > end_date:
                    logger.error("오류: 종료 날짜는 시작 날짜보다 빠를 수 없습니다.")
                    sys.exit(1)
                # 기간 설정
                current_date = start_date
                while current_date <= end_date:
                    dates_to_scrape.append(current_date)
                    current_date += datetime.timedelta(days=1)
                logger.info(f"수집 대상 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            else:
                # 시작 날짜 하루만
                dates_to_scrape.append(start_date)
                logger.info(f"수집 대상 날짜: {start_date.strftime('%Y-%m-%d')}")
        else:
            # 날짜 인수가 없으면 전전날 하루
            default_date = datetime.date.today() - datetime.timedelta(days=2)
            dates_to_scrape.append(default_date)
            logger.info(f"지정된 날짜 없음. 전전날 날짜 사용: {default_date.strftime('%Y-%m-%d')}")

    except ValueError:
        logger.error("오류: 날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        sys.exit(1)

    if not dates_to_scrape:
        logger.info("수집할 날짜가 없습니다.")
        sys.exit(0)

    # --- WebDriver 초기화 ---
    driver = setup_driver()
    if driver is None:
        logger.error("WebDriver를 초기화할 수 없습니다. 스크립트를 종료합니다.")
        sys.exit(1)

    initial_page_loaded = False
    try:
        # --- 초기 페이지 접속 및 설정 (한번만 수행) ---
        logger.info(f"초기 페이지 접속: {TARGET_URL}")
        driver.get(TARGET_URL)
        time.sleep(3) # 충분히 로딩 대기
        initial_page_loaded = True

        # --- 날짜별 반복 스크래핑 --- 
        total_dates = len(dates_to_scrape)
        success_count = 0
        fail_count = 0

        for i, target_date in enumerate(dates_to_scrape):
            if scrape_single_date(driver, target_date):
                success_count += 1
            else:
                fail_count += 1
            
            # 마지막 날짜가 아니면 대기
            if i < total_dates - 1:
                logger.info(f"\n다음 날짜 처리를 위해 {INTER_DATE_SLEEP_SECONDS}초 대기...")
                time.sleep(INTER_DATE_SLEEP_SECONDS)

        # 최종 결과 로깅 (print -> logger.info)
        logger.info(f"\n{'='*20} 전체 작업 완료 {'='*20}")
        logger.info(f"총 {total_dates}일 처리 시도, 성공: {success_count}, 실패: {fail_count}")

    except Exception as e:
        # 메인 로직 예외 로깅 (logger.exception 사용)
        logger.exception(f"스크립트 실행 중 예기치 않은 오류 발생: {e}") 
        if not initial_page_loaded:
             logger.warning("초기 페이지 로딩 단계에서 오류가 발생했을 수 있습니다.")
        # import traceback # 필요 없음
        # traceback.print_exc() # logger.exception이 처리
    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver 종료.")
        logger.info("스크립트 완전 종료.")
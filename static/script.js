document.addEventListener('DOMContentLoaded', () => {
    // 디버깅 용도로 콘솔 로그 추가
    console.log("스크립트 로드됨");

    // UI 요소 참조
    const statusElement = document.getElementById('scrape-status');
    const runButton = document.getElementById('run-scrape-btn');
    const stopButton = document.getElementById('stop-scrape-btn');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const runMessageElement = document.getElementById('run-message');
    const viewDateInput = document.getElementById('view-date-input');
    const viewDataButton = document.getElementById('view-data-btn');
    const keywordTableBody = document.getElementById('keyword-table-body');
    const loadingIndicator = document.getElementById('loading-indicator');
    const keywordTableContainer = document.getElementById('keyword-table-container');
    const noDataMessage = document.getElementById('no-data-message');
    const logOutputElement = document.getElementById('log-output');

    // UI 요소 존재 확인 (디버깅 목적)
    console.log('버튼 요소 확인:', {
        runButton: !!runButton,
        stopButton: !!stopButton,
        viewDataButton: !!viewDataButton,
        noDataMessage: !!noDataMessage
    });

    let statusInterval;
    let logInterval;

    // 페이지 로드 시 애니메이션 효과
    try {
        applyAnimations();
    } catch (error) {
        console.error('애니메이션 적용 오류:', error);
    }

    // --- 상태 확인 함수 ---
    async function checkStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            updateStatusUI(data.is_running, data.pid);
        } catch (error) {
            console.error('Error checking status:', error);
            updateStatusUI(null); // 상태 알 수 없음
        }
    }

    function updateStatusUI(isRunning, pid) {
        if (isRunning === true) {
            statusElement.textContent = '실행 중';
            statusElement.className = 'badge bg-success';
            runButton.disabled = true;
            stopButton.disabled = false;
        } else if (isRunning === false) {
            statusElement.textContent = '대기 중';
            statusElement.className = 'badge bg-warning text-dark';
            runButton.disabled = false;
            stopButton.disabled = true;
        } else {
            statusElement.textContent = '확인 실패';
            statusElement.className = 'badge bg-danger';
            runButton.disabled = true; // 오류 시 실행 불가
            stopButton.disabled = true; // 오류 시 중지 불가
        }
    }

    // --- 로그 업데이트 함수 ---
    async function updateLogs() {
        try {
            const response = await fetch('/api/logs?lines=100'); // 최신 100줄 요청
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            // textContent를 사용하여 HTML 인코딩 방지 및 개행 유지
            logOutputElement.textContent = data.logs;
            // 스크롤을 항상 맨 아래로 이동 (새 로그 확인 용이)
            logOutputElement.scrollTop = logOutputElement.scrollHeight;
        } catch (error) {
            console.error('Error updating logs:', error);
            logOutputElement.textContent = "로그 업데이트 중 오류 발생";
        }
    }

    // --- 날짜 목록 로드 함수 ---
    async function loadAvailableDates() {
        try {
            const response = await fetch('/api/dates');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.dates && data.dates.length > 0) {
                // 가장 최근 날짜를 선택 상자에 자동 설정
                const mostRecentDate = data.dates[0];
                viewDateInput.value = mostRecentDate;
                console.log('최근 날짜 설정됨:', mostRecentDate);
            }
        } catch (error) {
            console.error('Error loading dates:', error);
        }
    }

    // --- 키워드 로드 함수 ---
    async function loadKeywords(date) {
        console.log('키워드 로드 요청:', date);
        
        if (!date) {
            showNoDataMessage('데이터를 볼 날짜를 선택해주세요.');
            showKeywordTable(false);
            return;
        }
        
        showLoadingIndicator(true); // 로딩 시작
        showKeywordTable(false);    // 테이블 숨기기
        showNoDataMessage('', false); // 메시지 숨기기
        keywordTableBody.innerHTML = ''; // 기존 테이블 내용 지우기

        try {
            const response = await fetch(`/api/keywords/${date}`);
            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: '서버 응답 오류' }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log(`${date} 날짜 키워드 로드 성공:`, data.keywords.length);
            populateKeywordTable(data.keywords);
        } catch (error) {
            console.error(`Error loading keywords for ${date}:`, error);
            showNoDataMessage(`
                <i class="bi bi-exclamation-triangle-fill fs-1 d-block mb-3 text-warning"></i>
                키워드 로드 중 오류 발생:<br>${error.message}
            `, true, true);
        } finally {
            showLoadingIndicator(false); // 로딩 종료
        }
    }

    function populateKeywordTable(keywords) {
        if (!keywords || keywords.length === 0) {
            showNoDataMessage(`
                <i class="bi bi-inbox fs-1 d-block mb-3 text-secondary"></i>
                해당 날짜의 데이터가 없습니다.
            `, true, true);
            return;
        }
        
        // 테이블에 키워드 추가 (애니메이션 효과 포함)
        keywords.forEach((item, index) => {
            const row = document.createElement('tr');
            const rankCell = document.createElement('td');
            const keywordCell = document.createElement('td');
            
            // 순위에 따른 배지 스타일 적용
            if (item.rank <= 3) {
                rankCell.innerHTML = `<span class="badge bg-danger">${item.rank}</span>`;
            } else if (item.rank <= 10) {
                rankCell.innerHTML = `<span class="badge bg-warning text-dark">${item.rank}</span>`;
            } else {
                rankCell.innerHTML = `<span class="badge bg-secondary">${item.rank}</span>`;
            }
            
            keywordCell.textContent = item.keyword;
            row.appendChild(rankCell);
            row.appendChild(keywordCell);
            
            // 애니메이션 지연 효과
            row.style.opacity = '0';
            row.style.transform = 'translateY(10px)';
            row.style.transition = 'all 0.3s ease';
            row.style.transitionDelay = `${index * 0.03}s`;
            
            keywordTableBody.appendChild(row);
            
            // 강제 리플로우 후 애니메이션 적용
            setTimeout(() => {
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }, 10);
        });
        
        showKeywordTable(true);
        showNoDataMessage('', false); // 데이터 있으면 메시지 숨김
    }

    // 로딩 인디케이터 표시/숨김 함수
    function showLoadingIndicator(show) {
        loadingIndicator.style.display = show ? 'block' : 'none';
    }

    // 키워드 테이블 표시/숨김 함수
    function showKeywordTable(show) {
        keywordTableContainer.style.display = show ? 'block' : 'none';
    }

    // 데이터 없음/정보 메시지 표시/숨김 함수
    function showNoDataMessage(message, show = true, isHTML = false) {
        if (!noDataMessage) {
            console.error('noDataMessage 요소를 찾을 수 없습니다');
            return;
        }
        
        if (isHTML) {
            noDataMessage.innerHTML = message;
        } else {
            noDataMessage.textContent = message;
        }
        noDataMessage.style.display = show ? 'block' : 'none';
    }

    // --- 스크립트 실행/중지 함수 ---
    async function runScrape() {
        console.log('수동 실행 버튼 클릭됨');
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        showRunMessage('스크립트 실행 요청 중...', 'info');
        runButton.disabled = true;

        try {
            const response = await fetch('/api/run-scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ start_date: startDate || null, end_date: endDate || null })
            });

            let data;
            try {
                data = await response.json();
            } catch (e) {
                console.error('JSON 파싱 오류:', e);
                throw new Error('서버 응답을 처리하는 중 오류가 발생했습니다.');
            }

            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            console.log('스크립트 실행 응답:', data);
            showRunMessage(data.message, 'success');
            setTimeout(checkStatus, 500);
        } catch (error) {
            console.error('Error running scrape:', error);
            showRunMessage(`스크립트 실행 오류: ${error.message}`, 'danger');
            runButton.disabled = false;
        }
    }

    function showRunMessage(message, type = 'info') {
        runMessageElement.textContent = message;
        runMessageElement.className = `mt-3 alert alert-${type}`;
        runMessageElement.style.display = 'block';
        
        // 메시지 표시 애니메이션
        runMessageElement.style.opacity = '0';
        runMessageElement.style.transform = 'translateY(-10px)';
        
        // 강제 리플로우 후 애니메이션 적용
        setTimeout(() => {
            runMessageElement.style.transition = 'all 0.3s ease';
            runMessageElement.style.opacity = '1';
            runMessageElement.style.transform = 'translateY(0)';
        }, 10);
    }

    // --- 중지 함수 ---
    async function stopScrape() {
        console.log('중지 버튼 클릭됨');
        showRunMessage('스크립트 중지 요청 중...', 'info');
        stopButton.disabled = true;

        try {
            const response = await fetch('/api/stop-scrape', {
                method: 'POST',
            });
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }
            
            console.log('스크립트 중지 응답:', data);
            showRunMessage(data.message, 'success');
            setTimeout(checkStatus, 1500);
        } catch (error) {
            console.error('Error stopping scrape:', error);
            showRunMessage(`스크립트 중지 오류: ${error.message}`, 'danger');
            stopButton.disabled = false;
        }
    }
    
    // 초기 애니메이션 효과 적용
    function applyAnimations() {
        const fadeElements = document.querySelectorAll('.fade-in');
        fadeElements.forEach(el => {
            el.style.opacity = '1';
        });
    }

    // --- 이벤트 리스너 ---
    if (runButton) {
        runButton.addEventListener('click', () => {
            console.log('Run button clicked');
            runScrape();
        });
    } else {
        console.error('runButton을 찾을 수 없습니다');
    }
    
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            console.log('Stop button clicked');
            stopScrape();
        });
    } else {
        console.error('stopButton을 찾을 수 없습니다');
    }

    // 데이터 보기 버튼 클릭 시
    if (viewDataButton) {
        viewDataButton.addEventListener('click', () => {
            console.log('View data button clicked');
            const selectedDate = viewDateInput.value;
            if (selectedDate) {
                loadKeywords(selectedDate);
            } else {
                showNoDataMessage(`
                    <i class="bi bi-calendar-x fs-1 d-block mb-3 text-secondary"></i>
                    데이터를 볼 날짜를 선택해주세요.
                `, true, true);
                showKeywordTable(false);
            }
        });
    } else {
        console.error('viewDataButton을 찾을 수 없습니다');
    }

    // --- 초기화 ---
    console.log('초기화 시작');
    loadAvailableDates();
    checkStatus();
    updateLogs();
    
    try {
        showNoDataMessage(`
            <i class="bi bi-exclamation-circle fs-1 d-block mb-3 text-secondary"></i>
            날짜를 선택하고 '데이터 보기' 버튼을 클릭하세요.
        `, true, true);
    } catch (error) {
        console.error('showNoDataMessage 오류:', error);
    }
    
    showKeywordTable(false);
    
    // 주기적 업데이트
    statusInterval = setInterval(checkStatus, 5000);
    logInterval = setInterval(updateLogs, 10000);
    
    console.log('스크립트 초기화 완료');
}); 
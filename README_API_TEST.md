# 백엔드 API 테스트 가이드

이 문서는 Streamlit Platform 백엔드 API를 테스트하는 방법을 설명합니다.

## 🚀 테스트 방법

### 1. Python 스크립트 사용 (권장)

```bash
# 필요한 패키지 설치
pip install requests

# 테스트 실행
python test_backend_api.py
```

**장점:**
- 자동화된 테스트 실행
- 상세한 응답 정보 출력
- 토큰 자동 관리
- 테스트 결과 요약 제공

### 2. cURL 스크립트 사용

```bash
# 실행 권한 부여 (Linux/Mac)
chmod +x test_api_curl.sh

# 테스트 실행
./test_api_curl.sh

# Windows에서는 Git Bash 사용
bash test_api_curl.sh
```

**장점:**
- 별도 설치 없이 사용 가능
- 각 API 호출을 개별적으로 확인 가능
- 디버깅에 유용

### 3. Postman 사용

1. Postman 실행
2. `Streamlit_Platform_API.postman_collection.json` 파일 import
3. Collection 변수 확인:
   - `baseUrl`: http://localhost:8000
   - `token`: 자동으로 설정됨
   - `appId`: 자동으로 설정됨
4. 순서대로 API 호출 실행

**장점:**
- GUI 환경에서 편리한 테스트
- 응답 데이터 시각화
- 히스토리 관리

## 📋 테스트 시나리오

### 1단계: 기본 연결 확인
- ✅ 헬스 체크 (`GET /`)
- ✅ API 헬스 체크 (`GET /api/health`)

### 2단계: 사용자 인증
- ✅ 사용자 등록 (`POST /api/auth/register`)
- ✅ 사용자 로그인 (`POST /api/auth/login`)
- ✅ 현재 사용자 정보 조회 (`GET /api/auth/me`)

### 3단계: 앱 관리
- ✅ 앱 생성 (`POST /api/apps/`)
- ✅ 앱 목록 조회 (`GET /api/apps/`)

### 4단계: 배포 및 모니터링
- ✅ 앱 배포 (`POST /api/apps/{id}/deploy`)
- ✅ 앱 상세 정보 조회 (`GET /api/apps/{id}`)
- ✅ 앱 로그 조회 (`GET /api/apps/{id}/logs`)
- ✅ 앱 중지 (`POST /api/apps/{id}/stop`)

## 🔍 테스트 대상 저장소

**GitHub 저장소:** https://github.com/sungreong/ZoneCleaner
- **메인 파일:** `app.py`
- **브랜치:** `main`
- **설명:** Streamlit 기반 데이터 클리닝 도구

## 📊 예상 결과

### 성공적인 테스트 결과:
1. **헬스 체크**: 200 OK, 서버 상태 정상
2. **사용자 등록**: 200 OK, 사용자 생성 완료
3. **로그인**: 200 OK, JWT 토큰 발급
4. **앱 생성**: 200 OK, 앱 메타데이터 저장
5. **앱 배포**: 200 OK, Docker 컨테이너 생성 및 실행
6. **로그 조회**: 200 OK, Streamlit 앱 실행 로그 확인

### 실패 가능한 지점:
1. **Docker 연결 실패**: Docker 서비스가 실행되지 않은 경우
2. **Git 클론 실패**: 네트워크 문제 또는 저장소 접근 권한
3. **이미지 빌드 실패**: requirements.txt 의존성 문제
4. **컨테이너 실행 실패**: 포트 충돌 또는 리소스 부족

## 🛠️ 디버깅 팁

### 1. 로그 확인
```bash
# 백엔드 컨테이너 로그
docker logs streamlit_platform_backend -f

# 특정 앱 컨테이너 로그
docker logs <container_name> -f
```

### 2. 컨테이너 상태 확인
```bash
# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인 (중지된 것 포함)
docker ps -a
```

### 3. 네트워크 확인
```bash
# Docker 네트워크 확인
docker network ls
docker network inspect streamlit_network
```

### 4. 데이터베이스 확인
```bash
# PostgreSQL 접속
docker exec -it streamlit_platform_db psql -U postgres -d streamlit_platform

# 테이블 확인
\dt

# 앱 데이터 확인
SELECT * FROM apps;
```

## 🚨 문제 해결

### 1. "Docker 클라이언트가 연결되지 않았습니다" 에러
- Docker 서비스가 실행 중인지 확인
- Docker 소켓 권한 확인
- 백엔드 컨테이너 재시작

### 2. "Git 저장소 클론 실패" 에러
- 인터넷 연결 확인
- GitHub 저장소 접근 가능 여부 확인
- 프록시 설정 확인

### 3. "이미지 빌드 실패" 에러
- requirements.txt 파일 존재 여부 확인
- Python 패키지 의존성 문제 확인
- Docker 이미지 빌드 로그 확인

### 4. API 응답 시간 초과
- 서버 리소스 확인
- 네트워크 상태 확인
- 타임아웃 설정 조정

## 📈 성능 테스트

### 부하 테스트 (선택사항)
```bash
# Apache Bench 사용
ab -n 100 -c 10 http://localhost:8000/api/health

# 또는 Python으로 간단한 부하 테스트
python -c "
import requests
import time
import concurrent.futures

def test_api():
    response = requests.get('http://localhost:8000/api/health')
    return response.status_code

start_time = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(test_api) for _ in range(100)]
    results = [future.result() for future in futures]

end_time = time.time()
success_count = sum(1 for r in results if r == 200)
print(f'성공: {success_count}/100, 소요시간: {end_time - start_time:.2f}초')
"
```

## 📝 테스트 체크리스트

- [ ] 백엔드 서버 실행 확인
- [ ] Docker 서비스 실행 확인
- [ ] PostgreSQL 데이터베이스 연결 확인
- [ ] 기본 API 엔드포인트 응답 확인
- [ ] 사용자 인증 플로우 테스트
- [ ] 앱 생성 및 배포 테스트
- [ ] 로그 조회 기능 테스트
- [ ] 에러 처리 확인
- [ ] 성능 및 응답 시간 확인

이 가이드를 따라 체계적으로 백엔드 API를 테스트하면 시스템의 안정성과 기능을 확인할 수 있습니다. 
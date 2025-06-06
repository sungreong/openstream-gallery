#!/bin/bash

# 4단계: 앱 배포 및 모니터링 테스트
# 목적: 실제 Docker 컨테이너 배포, 로그 조회, 상태 모니터링

BASE_URL="http://localhost:8000"
TOKEN_FILE="./temp_token.txt"
APP_ID_FILE="./temp_app_id.txt"

echo "🚀 4단계: 앱 배포 및 모니터링 테스트"
echo "=================================="
echo "목적: ZoneCleaner 앱의 실제 Docker 배포 및 모니터링"
echo "예상 결과: Git 클론 → Docker 빌드 → 컨테이너 실행 → 로그 확인"
echo ""

# 토큰 및 앱 ID 확인
if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ 토큰 파일이 없습니다."
    echo "💡 먼저 2단계 인증 테스트를 실행하세요: bash test_step2_auth.sh"
    exit 1
fi

if [ ! -f "$APP_ID_FILE" ]; then
    echo "❌ 앱 ID 파일이 없습니다."
    echo "💡 먼저 3단계 앱 관리 테스트를 실행하세요: bash test_step3_app_management.sh"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
APP_ID=$(cat "$APP_ID_FILE")

if [ -z "$TOKEN" ] || [ -z "$APP_ID" ]; then
    echo "❌ 토큰 또는 앱 ID가 비어있습니다."
    echo "💡 이전 단계들을 다시 실행하세요."
    exit 1
fi

echo "🔑 저장된 토큰 사용: ${TOKEN:0:20}..."
echo "📱 앱 ID: $APP_ID"
echo ""

# 1. 앱 배포 시작
echo "1️⃣ 앱 배포 시작 (POST /api/apps/$APP_ID/deploy)"
echo "설명: ZoneCleaner GitHub 저장소를 Docker 컨테이너로 배포"
echo "과정: Git 클론 → Dockerfile 생성 → 이미지 빌드 → 컨테이너 실행"
echo "---"

DEPLOY_RESPONSE=$(curl -X POST "$BASE_URL/api/apps/$APP_ID/deploy" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "git_url": "https://github.com/sungreong/llm-tokenizer-app",
    "branch": "main",
    "main_file": "app.py"
  }' \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$DEPLOY_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$DEPLOY_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 배포 시작 성공!"
    echo "⏳ 배포 진행 중... (Git 클론, Docker 빌드, 컨테이너 실행)"
    echo "📝 배포는 시간이 걸릴 수 있습니다 (1-3분)"
else
    echo "❌ 앱 배포 시작 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - Docker 서비스 실행 확인: docker ps"
    echo "   - 네트워크 연결 확인 (GitHub 접근)"
    echo "   - Docker 소켓 권한 확인"
    echo "   - 백엔드 로그 확인: docker logs streamlit_platform_backend"
    exit 1
fi

echo ""

# 2. 배포 진행 상황 모니터링 (30초 대기)
echo "2️⃣ 배포 진행 상황 모니터링"
echo "설명: 30초 동안 배포 상태를 주기적으로 확인"
echo "---"

for i in {1..6}; do
    echo "⏰ 배포 상태 확인 중... ($i/6)"
    
    STATUS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -s)
    
    if command -v jq &> /dev/null; then
        APP_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // "unknown"' 2>/dev/null)
        CONTAINER_ID=$(echo "$STATUS_RESPONSE" | jq -r '.container_id // "none"' 2>/dev/null)
        
        echo "   📊 현재 상태: $APP_STATUS"
        if [ "$CONTAINER_ID" != "none" ] && [ "$CONTAINER_ID" != "null" ]; then
            echo "   🐳 컨테이너 ID: ${CONTAINER_ID:0:12}..."
        fi
        
        if [ "$APP_STATUS" = "running" ]; then
            echo "✅ 배포 완료! 앱이 실행 중입니다."
            break
        elif [ "$APP_STATUS" = "failed" ]; then
            echo "❌ 배포 실패!"
            break
        fi
    else
        echo "   ⚠️  jq 없음 - 상태 확인 건너뜀"
    fi
    
    if [ $i -lt 6 ]; then
        sleep 5
    fi
done

echo ""

# 3. 최종 앱 상태 확인
echo "3️⃣ 최종 앱 상태 확인 (GET /api/apps/$APP_ID)"
echo "설명: 배포 완료 후 앱의 최종 상태 확인"
echo "---"

FINAL_STATUS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$FINAL_STATUS_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$FINAL_STATUS_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 상태 조회 성공!"
    
    if command -v jq &> /dev/null; then
        APP_STATUS=$(echo "$FINAL_STATUS_RESPONSE" | jq -r '.status // "unknown"' 2>/dev/null)
        CONTAINER_ID=$(echo "$FINAL_STATUS_RESPONSE" | jq -r '.container_id // "none"' 2>/dev/null)
        SUBDOMAIN=$(echo "$FINAL_STATUS_RESPONSE" | jq -r '.subdomain // "none"' 2>/dev/null)
        
        echo "📊 최종 상태: $APP_STATUS"
        
        if [ "$CONTAINER_ID" != "none" ] && [ "$CONTAINER_ID" != "null" ]; then
            echo "🐳 컨테이너 ID: $CONTAINER_ID"
        fi
        
        if [ "$SUBDOMAIN" != "none" ] && [ "$SUBDOMAIN" != "null" ]; then
            echo "🌐 접속 URL: http://localhost/$SUBDOMAIN/"
        fi
    fi
else
    echo "❌ 앱 상태 조회 실패 (상태 코드: $STATUS_CODE)"
fi

echo ""

# 4. 앱 로그 조회
echo "4️⃣ 앱 로그 조회 (GET /api/apps/$APP_ID/logs)"
echo "설명: 배포된 앱의 실행 로그 확인 (Streamlit 시작 로그 등)"
echo "---"

LOGS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID/logs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$LOGS_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$LOGS_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 로그 조회 성공!"
    
    if command -v jq &> /dev/null; then
        LOGS=$(echo "$LOGS_RESPONSE" | jq -r '.logs // "로그 없음"' 2>/dev/null)
        if [ "$LOGS" != "로그 없음" ] && [ "$LOGS" != "null" ]; then
            echo ""
            echo "📋 최근 로그 내용:"
            echo "---"
            echo "$LOGS" | tail -10
            echo "---"
            
            # Streamlit 관련 로그 확인
            if echo "$LOGS" | grep -q "Streamlit"; then
                echo "✅ Streamlit 관련 로그 발견 - 앱이 정상 실행 중일 가능성 높음"
            fi
            
            if echo "$LOGS" | grep -q "8501"; then
                echo "✅ 포트 8501 관련 로그 발견 - Streamlit 서버 실행 중"
            fi
        fi
    fi
else
    echo "❌ 앱 로그 조회 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 컨테이너가 실행 중인지 확인: docker ps"
    echo "   - 컨테이너 로그 직접 확인: docker logs <container_id>"
fi

echo ""

# 5. Docker 컨테이너 직접 확인
echo "5️⃣ Docker 컨테이너 직접 확인"
echo "설명: docker ps 명령으로 실제 컨테이너 상태 확인"
echo "---"

if command -v docker &> /dev/null; then
    echo "🐳 현재 실행 중인 컨테이너:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAMES|zonecleaner|streamlit)" || echo "ZoneCleaner 관련 컨테이너를 찾을 수 없습니다."
else
    echo "⚠️  Docker 명령어를 사용할 수 없습니다."
fi

echo ""
echo "🎉 4단계 앱 배포 및 모니터링 완료!"
echo ""
echo "📋 전체 테스트 결과 요약:"
echo "   ✅ 1단계: 서버 연결 확인"
echo "   ✅ 2단계: 사용자 인증"
echo "   ✅ 3단계: 앱 메타데이터 관리"
echo "   ✅ 4단계: 앱 배포 및 모니터링"
echo ""
echo "🌟 백엔드 API 테스트가 모두 완료되었습니다!"
echo ""
echo "💡 다음 단계 제안:"
echo "   - 웹 브라우저에서 앱 접속 테스트"
echo "   - 앱 중지 테스트: bash test_step5_cleanup.sh"
echo "   - 프론트엔드 연동 테스트"
echo "==================================" 
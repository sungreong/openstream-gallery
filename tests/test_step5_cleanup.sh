#!/bin/bash

# 5단계: 정리 및 앱 중지 테스트
# 목적: 배포된 앱 중지, 리소스 정리, 테스트 파일 정리

BASE_URL="http://localhost:8000"
TOKEN_FILE="./temp_token.txt"
APP_ID_FILE="./temp_app_id.txt"

echo "🧹 5단계: 정리 및 앱 중지 테스트"
echo "=================================="
echo "목적: 배포된 앱 중지 및 테스트 환경 정리"
echo "예상 결과: 컨테이너 중지 → 리소스 해제 → 임시 파일 정리"
echo ""

# 토큰 및 앱 ID 확인
if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ 토큰 파일이 없습니다."
    echo "💡 이미 정리되었거나 이전 단계를 실행하지 않았습니다."
    exit 1
fi

if [ ! -f "$APP_ID_FILE" ]; then
    echo "❌ 앱 ID 파일이 없습니다."
    echo "💡 이미 정리되었거나 앱이 생성되지 않았습니다."
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
APP_ID=$(cat "$APP_ID_FILE")

if [ -z "$TOKEN" ] || [ -z "$APP_ID" ]; then
    echo "❌ 토큰 또는 앱 ID가 비어있습니다."
    exit 1
fi

echo "🔑 저장된 토큰 사용: ${TOKEN:0:20}..."
echo "📱 앱 ID: $APP_ID"
echo ""

# 1. 현재 앱 상태 확인
echo "1️⃣ 현재 앱 상태 확인 (GET /api/apps/$APP_ID)"
echo "설명: 중지하기 전 현재 앱 상태 확인"
echo "---"

STATUS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$STATUS_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$STATUS_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 상태 조회 성공!"
    
    if command -v jq &> /dev/null; then
        APP_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // "unknown"' 2>/dev/null)
        CONTAINER_ID=$(echo "$STATUS_RESPONSE" | jq -r '.container_id // "none"' 2>/dev/null)
        
        echo "📊 현재 상태: $APP_STATUS"
        
        if [ "$CONTAINER_ID" != "none" ] && [ "$CONTAINER_ID" != "null" ]; then
            echo "🐳 컨테이너 ID: $CONTAINER_ID"
        fi
        
        if [ "$APP_STATUS" = "stopped" ]; then
            echo "ℹ️  앱이 이미 중지되어 있습니다."
        fi
    fi
else
    echo "❌ 앱 상태 조회 실패 (상태 코드: $STATUS_CODE)"
    echo "⚠️  앱이 존재하지 않거나 이미 삭제되었을 수 있습니다."
fi

echo ""

# 2. 앱 중지
echo "2️⃣ 앱 중지 (POST /api/apps/$APP_ID/stop)"
echo "설명: 실행 중인 Docker 컨테이너 중지"
echo "---"

STOP_RESPONSE=$(curl -X POST "$BASE_URL/api/apps/$APP_ID/stop" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$STOP_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$STOP_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 중지 성공!"
    echo "🐳 Docker 컨테이너가 중지되었습니다."
else
    echo "❌ 앱 중지 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 앱이 이미 중지되어 있는지 확인"
    echo "   - Docker 컨테이너 상태 직접 확인: docker ps"
    echo "   - 수동으로 컨테이너 중지: docker stop <container_id>"
fi

echo ""

# 3. 중지 후 상태 확인
echo "3️⃣ 중지 후 상태 확인 (GET /api/apps/$APP_ID)"
echo "설명: 앱이 정상적으로 중지되었는지 확인"
echo "---"

sleep 2  # 중지 처리 시간 대기

FINAL_STATUS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$FINAL_STATUS_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$FINAL_STATUS_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 최종 상태 조회 성공!"
    
    if command -v jq &> /dev/null; then
        APP_STATUS=$(echo "$FINAL_STATUS_RESPONSE" | jq -r '.status // "unknown"' 2>/dev/null)
        echo "📊 최종 상태: $APP_STATUS"
        
        if [ "$APP_STATUS" = "stopped" ]; then
            echo "✅ 앱이 성공적으로 중지되었습니다."
        else
            echo "⚠️  앱 상태가 예상과 다릅니다: $APP_STATUS"
        fi
    fi
else
    echo "❌ 최종 상태 조회 실패 (상태 코드: $STATUS_CODE)"
fi

echo ""

# 4. Docker 컨테이너 상태 확인
echo "4️⃣ Docker 컨테이너 상태 확인"
echo "설명: ZoneCleaner 관련 컨테이너가 중지되었는지 확인"
echo "---"

if command -v docker &> /dev/null; then
    echo "🐳 현재 실행 중인 컨테이너 (ZoneCleaner 관련):"
    RUNNING_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(zonecleaner|streamlit)" || echo "")
    
    if [ -z "$RUNNING_CONTAINERS" ]; then
        echo "✅ ZoneCleaner 관련 컨테이너가 실행 중이지 않습니다."
    else
        echo "$RUNNING_CONTAINERS"
        echo "⚠️  일부 컨테이너가 여전히 실행 중입니다."
    fi
    
    echo ""
    echo "🗑️  중지된 컨테이너 (최근 10개):"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}" | head -11 | grep -E "(NAMES|zonecleaner|streamlit|Exited)" || echo "관련 컨테이너를 찾을 수 없습니다."
else
    echo "⚠️  Docker 명령어를 사용할 수 없습니다."
fi

echo ""

# 5. 임시 파일 정리
echo "5️⃣ 임시 파일 정리"
echo "설명: 테스트 중 생성된 임시 파일들 삭제"
echo "---"

FILES_TO_CLEAN=("$TOKEN_FILE" "$APP_ID_FILE")
CLEANED_COUNT=0

for file in "${FILES_TO_CLEAN[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "🗑️  삭제됨: $file"
        CLEANED_COUNT=$((CLEANED_COUNT + 1))
    else
        echo "ℹ️  파일 없음: $file"
    fi
done

echo "✅ 총 $CLEANED_COUNT개의 임시 파일이 정리되었습니다."

echo ""

# 6. 선택적 Docker 이미지 정리
echo "6️⃣ Docker 이미지 정리 (선택사항)"
echo "설명: 테스트 중 생성된 Docker 이미지 확인"
echo "---"

if command -v docker &> /dev/null; then
    echo "🐳 ZoneCleaner 관련 Docker 이미지:"
    ZONECLEANER_IMAGES=$(docker images | grep -i zonecleaner || echo "")
    
    if [ -n "$ZONECLEANER_IMAGES" ]; then
        echo "$ZONECLEANER_IMAGES"
        echo ""
        echo "💡 이미지를 삭제하려면 다음 명령어를 사용하세요:"
        echo "   docker rmi \$(docker images | grep zonecleaner | awk '{print \$3}')"
    else
        echo "ℹ️  ZoneCleaner 관련 이미지를 찾을 수 없습니다."
    fi
else
    echo "⚠️  Docker 명령어를 사용할 수 없습니다."
fi

echo ""
echo "🎉 5단계 정리 및 앱 중지 완료!"
echo ""
echo "📋 정리 작업 요약:"
echo "   ✅ 앱 상태 확인"
echo "   ✅ 앱 중지 요청"
echo "   ✅ 중지 상태 검증"
echo "   ✅ Docker 컨테이너 상태 확인"
echo "   ✅ 임시 파일 정리"
echo "   ✅ Docker 이미지 확인"
echo ""
echo "🌟 모든 테스트 및 정리가 완료되었습니다!"
echo ""
echo "💡 전체 테스트 재실행:"
echo "   bash test_step1_health.sh"
echo "   bash test_step2_auth.sh"
echo "   bash test_step3_app_management.sh"
echo "   bash test_step4_deployment.sh"
echo "   bash test_step5_cleanup.sh"
echo "==================================" 
#!/bin/bash

# 3단계: 앱 관리 테스트
# 목적: 앱 생성, 목록 조회 기능 확인

BASE_URL="http://localhost:8000"
TOKEN_FILE="./temp_token.txt"
APP_ID_FILE="./temp_app_id.txt"

echo "📱 3단계: 앱 관리 테스트"
echo "=================================="
echo "목적: 앱 생성 및 목록 조회 기능 확인"
echo "예상 결과: 앱 메타데이터 저장 → 목록에서 확인"
echo ""

# 토큰 확인
if [ ! -f "$TOKEN_FILE" ]; then
    echo "❌ 토큰 파일이 없습니다."
    echo "💡 먼저 2단계 인증 테스트를 실행하세요: bash test_step2_auth.sh"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰이 비어있습니다."
    echo "💡 먼저 2단계 인증 테스트를 실행하세요: bash test_step2_auth.sh"
    exit 1
fi

echo "🔑 저장된 토큰 사용: ${TOKEN:0:20}..."
echo ""

# 1. 앱 생성 (베이스 Dockerfile 타입 선택)
echo "1️⃣ 앱 생성 (POST /api/apps/)"
echo "설명: llm tokenizer GitHub 저장소로 새 앱 생성"
echo "저장소: https://github.com/sungreong/llm-tokenizer"
echo "베이스 Dockerfile: 데이터사이언스 버전 (py309) - numpy 사용으로 인해"
echo "---"
APP_RESPONSE=$(curl -X POST "$BASE_URL/api/apps/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "llm tokenizer",
    "description": "GitHub에서 가져온 테스트 앱 - 데이터 클리닝 도구",
    "git_url": "https://github.com/sungreong/llm-tokenizer-app",
    "branch": "main",
    "main_file": "app.py",
    "base_dockerfile_type": "py309"
  }' \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$APP_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$APP_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 생성 성공!"
    
    # 앱 ID 추출 및 저장 (jq가 있는 경우)
    if command -v jq &> /dev/null; then
        APP_ID=$(echo "$APP_RESPONSE" | jq -r '.id // empty' 2>/dev/null)
        if [ -n "$APP_ID" ] && [ "$APP_ID" != "null" ]; then
            echo "$APP_ID" > "$APP_ID_FILE"
            echo "📱 앱 ID 저장됨: $APP_ID"
        else
            echo "⚠️  앱 ID 추출 실패 (jq 파싱 오류)"
        fi
    else
        echo "⚠️  jq가 설치되지 않아 앱 ID 자동 추출을 건너뜁니다."
    fi
else
    echo "❌ 앱 생성 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 토큰 유효성 확인"
    echo "   - 앱 스키마 및 모델 확인"
    echo "   - 데이터베이스 연결 확인"
    echo "   - 백엔드 로그 확인: docker logs streamlit_platform_backend"
    exit 1
fi

echo ""

# 2. 앱 목록 조회
echo "2️⃣ 앱 목록 조회 (GET /api/apps/)"
echo "설명: 생성된 앱이 목록에 나타나는지 확인"
echo "---"
APPS_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$APPS_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$APPS_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 앱 목록 조회 성공!"
    
    # 앱 개수 확인 (jq가 있는 경우)
    if command -v jq &> /dev/null; then
        APP_COUNT=$(echo "$APPS_RESPONSE" | jq '. | length' 2>/dev/null)
        if [ -n "$APP_COUNT" ] && [ "$APP_COUNT" != "null" ]; then
            echo "📊 총 앱 개수: $APP_COUNT개"
            
            # ZoneCleaner 앱이 있는지 확인
            ZONECLEANER_EXISTS=$(echo "$APPS_RESPONSE" | jq '.[] | select(.name | contains("ZoneCleaner"))' 2>/dev/null)
            if [ -n "$ZONECLEANER_EXISTS" ]; then
                echo "✅ ZoneCleaner 앱이 목록에서 확인됨"
            else
                echo "⚠️  ZoneCleaner 앱이 목록에서 찾을 수 없음"
            fi
        fi
    fi
else
    echo "❌ 앱 목록 조회 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 토큰 유효성 확인"
    echo "   - 앱 조회 권한 확인"
    echo "   - 데이터베이스 쿼리 확인"
    exit 1
fi

echo ""

# 3. 앱 상세 정보 조회 (앱 ID가 있는 경우)
if [ -f "$APP_ID_FILE" ]; then
    APP_ID=$(cat "$APP_ID_FILE")
    
    echo "3️⃣ 앱 상세 정보 조회 (GET /api/apps/$APP_ID)"
    echo "설명: 생성된 앱의 상세 정보 확인"
    echo "---"
    
    APP_DETAIL_RESPONSE=$(curl -X GET "$BASE_URL/api/apps/$APP_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s)
    
    echo "$APP_DETAIL_RESPONSE"
    
    # 상태 코드 추출
    STATUS_CODE=$(echo "$APP_DETAIL_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)
    
    if [ "$STATUS_CODE" = "200" ]; then
        echo "✅ 앱 상세 정보 조회 성공!"
        
        # 앱 상태 확인 (jq가 있는 경우)
        if command -v jq &> /dev/null; then
            APP_STATUS=$(echo "$APP_DETAIL_RESPONSE" | jq -r '.status // empty' 2>/dev/null)
            if [ -n "$APP_STATUS" ] && [ "$APP_STATUS" != "null" ]; then
                echo "📊 앱 상태: $APP_STATUS"
            fi
        fi
    else
        echo "❌ 앱 상세 정보 조회 실패 (상태 코드: $STATUS_CODE)"
        echo "💡 해결 방법:"
        echo "   - 앱 ID 유효성 확인"
        echo "   - 앱 조회 권한 확인"
    fi
else
    echo "3️⃣ 앱 상세 정보 조회 건너뜀 (앱 ID 없음)"
fi

echo ""
echo "🎉 3단계 앱 관리 완료!"
echo "✅ 앱 생성 및 목록 조회가 성공했습니다."
echo ""
echo "📋 현재까지 완료된 기능:"
echo "   ✅ 서버 연결"
echo "   ✅ 사용자 인증"
echo "   ✅ 앱 메타데이터 관리"
echo ""
echo "다음 단계: 앱 배포 및 모니터링 테스트"
echo "실행 명령: bash test_step4_deployment.sh"
echo "==================================" 
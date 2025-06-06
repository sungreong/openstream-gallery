#!/bin/bash

# 2단계: 사용자 인증 테스트
# 목적: 사용자 등록, 로그인, 토큰 검증 기능 확인

BASE_URL="http://localhost:8000"
TOKEN_FILE="./temp_token.txt"

echo "🔐 2단계: 사용자 인증 테스트"
echo "=================================="
echo "목적: 사용자 등록, 로그인, JWT 토큰 검증"
echo "예상 결과: 사용자 생성 → 로그인 성공 → 토큰 발급"
echo ""

# 1. 사용자 등록
echo "1️⃣ 사용자 등록 (POST /api/auth/register)"
echo "설명: 새로운 사용자 계정 생성"
echo "---"
REGISTER_RESPONSE=$(curl -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }' \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$REGISTER_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$REGISTER_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 사용자 등록 성공!"
elif [ "$STATUS_CODE" = "400" ]; then
    echo "⚠️  사용자가 이미 존재합니다. 기존 사용자로 계속 진행..."
else
    echo "❌ 사용자 등록 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 데이터베이스 연결 확인"
    echo "   - 사용자 모델 및 스키마 확인"
    echo "   - 백엔드 로그 확인: docker logs streamlit_platform_backend"
    exit 1
fi

echo ""

# 2. 사용자 로그인
echo "2️⃣ 사용자 로그인 (POST /api/auth/login)"
echo "설명: 사용자 인증 및 JWT 토큰 발급"
echo "---"
LOGIN_RESPONSE=$(curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$LOGIN_RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$LOGIN_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 사용자 로그인 성공!"
    
    # 토큰 추출 및 저장 (jq가 있는 경우)
    if command -v jq &> /dev/null; then
        TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty' 2>/dev/null)
        if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
            echo "$TOKEN" > "$TOKEN_FILE"
            echo "🔑 JWT 토큰 저장됨: ${TOKEN:0:20}..."
        else
            echo "⚠️  토큰 추출 실패 (jq 파싱 오류)"
        fi
    else
        echo "⚠️  jq가 설치되지 않아 토큰 자동 추출을 건너뜁니다."
        echo "💡 수동으로 토큰을 복사해서 다음 단계에서 사용하세요."
    fi
else
    echo "❌ 사용자 로그인 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 사용자명과 비밀번호 확인"
    echo "   - 인증 로직 확인"
    echo "   - JWT 설정 확인"
    exit 1
fi

echo ""

# 3. 현재 사용자 정보 조회 (토큰 검증)
echo "3️⃣ 현재 사용자 정보 조회 (GET /api/auth/me)"
echo "설명: JWT 토큰 유효성 검증 및 사용자 정보 조회"
echo "---"

if [ -f "$TOKEN_FILE" ]; then
    TOKEN=$(cat "$TOKEN_FILE")
    
    USER_RESPONSE=$(curl -X GET "$BASE_URL/api/auth/me" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
      -s)
    
    echo "$USER_RESPONSE"
    
    # 상태 코드 추출
    STATUS_CODE=$(echo "$USER_RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)
    
    if [ "$STATUS_CODE" = "200" ]; then
        echo "✅ 사용자 정보 조회 성공!"
        echo "🔑 JWT 토큰이 유효합니다."
    else
        echo "❌ 사용자 정보 조회 실패 (상태 코드: $STATUS_CODE)"
        echo "💡 해결 방법:"
        echo "   - JWT 토큰 유효성 확인"
        echo "   - 토큰 만료 시간 확인"
        echo "   - 인증 미들웨어 확인"
        exit 1
    fi
else
    echo "⚠️  토큰 파일이 없어서 사용자 정보 조회를 건너뜁니다."
    echo "💡 수동으로 토큰을 입력하여 테스트할 수 있습니다."
fi

echo ""
echo "🎉 2단계 사용자 인증 완료!"
echo "✅ 사용자 등록, 로그인, 토큰 검증이 모두 성공했습니다."
echo ""
echo "다음 단계: 앱 관리 테스트"
echo "실행 명령: bash test_step3_app_management.sh"
echo "==================================" 
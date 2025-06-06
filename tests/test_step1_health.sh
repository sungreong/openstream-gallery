#!/bin/bash

# 1단계: 헬스 체크 테스트
# 목적: 백엔드 서버가 정상적으로 실행되고 있는지 확인

BASE_URL="http://localhost:8000"

echo "🏥 1단계: 헬스 체크 테스트"
echo "=================================="
echo "목적: 백엔드 서버 연결 상태 확인"
echo "예상 결과: 200 OK 응답"
echo ""

# 1. 기본 헬스 체크
echo "1️⃣ 기본 헬스 체크 (GET /)"
echo "설명: 서버가 실행 중인지 확인"
echo "---"
RESPONSE=$(curl -X GET "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ 기본 헬스 체크 성공!"
else
    echo "❌ 기본 헬스 체크 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - 백엔드 서버가 실행 중인지 확인: docker ps"
    echo "   - 포트 8000이 사용 가능한지 확인"
    echo "   - 방화벽 설정 확인"
    exit 1
fi

echo ""

# 2. API 헬스 체크
echo "2️⃣ API 헬스 체크 (GET /api/health)"
echo "설명: API 엔드포인트가 정상 작동하는지 확인"
echo "---"
RESPONSE=$(curl -X GET "$BASE_URL/api/health" \
  -H "Content-Type: application/json" \
  -w "\n상태 코드: %{http_code}\n응답 시간: %{time_total}초\n" \
  -s)

echo "$RESPONSE"

# 상태 코드 추출
STATUS_CODE=$(echo "$RESPONSE" | grep "상태 코드:" | cut -d' ' -f3)

if [ "$STATUS_CODE" = "200" ]; then
    echo "✅ API 헬스 체크 성공!"
else
    echo "❌ API 헬스 체크 실패 (상태 코드: $STATUS_CODE)"
    echo "💡 해결 방법:"
    echo "   - FastAPI 라우터가 올바르게 등록되었는지 확인"
    echo "   - /api/health 엔드포인트 구현 확인"
    echo "   - 백엔드 로그 확인: docker logs streamlit_platform_backend"
    exit 1
fi

echo ""
echo "🎉 1단계 헬스 체크 완료!"
echo "✅ 백엔드 서버가 정상적으로 실행 중입니다."
echo ""
echo "다음 단계: 사용자 인증 테스트"
echo "실행 명령: bash test_step2_auth.sh"
echo "==================================" 
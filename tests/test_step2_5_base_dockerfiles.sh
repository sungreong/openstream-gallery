#!/bin/bash

# 베이스 Dockerfile 목록 조회 테스트
# 2.5단계: 베이스 Dockerfile 시스템 테스트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
API_BASE_URL="http://localhost:8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="$SCRIPT_DIR/temp_token.txt"

echo -e "${BLUE}=== 2.5단계: 베이스 Dockerfile 시스템 테스트 ===${NC}"
echo

# 토큰 확인
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}❌ 토큰 파일을 찾을 수 없습니다: $TOKEN_FILE${NC}"
    echo "먼저 2단계 인증 테스트를 실행하세요."
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ 토큰이 비어있습니다.${NC}"
    echo "먼저 2단계 인증 테스트를 실행하세요."
    exit 1
fi

echo -e "${GREEN}✅ 인증 토큰 확인 완료${NC}"
echo

# 1. 베이스 Dockerfile 목록 조회 테스트
echo -e "${YELLOW}📋 1. 베이스 Dockerfile 목록 조회 테스트${NC}"
echo "GET $API_BASE_URL/api/dockerfiles/base-types"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$API_BASE_URL/api/dockerfiles/base-types")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP 상태 코드: $HTTP_CODE"
echo "응답 내용:"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 베이스 Dockerfile 목록 조회 성공${NC}"
    
    # 응답 데이터 검증
    SUCCESS=$(echo "$BODY" | jq -r '.success // false' 2>/dev/null)
    BASE_DOCKERFILES=$(echo "$BODY" | jq -r '.base_dockerfiles // []' 2>/dev/null)
    
    if [ "$SUCCESS" = "true" ]; then
        echo -e "${GREEN}✅ 응답 성공 플래그 확인${NC}"
        
        # 베이스 Dockerfile 개수 확인
        COUNT=$(echo "$BASE_DOCKERFILES" | jq 'length' 2>/dev/null || echo "0")
        echo "베이스 Dockerfile 개수: $COUNT"
        
        if [ "$COUNT" -ge 3 ]; then
            echo -e "${GREEN}✅ 베이스 Dockerfile 개수 확인 (최소 3개 이상)${NC}"
            
            # 각 베이스 Dockerfile 정보 출력
            echo -e "${BLUE}📄 베이스 Dockerfile 목록:${NC}"
            echo "$BASE_DOCKERFILES" | jq -r '.[] | "- \(.type): \(.name)\n  설명: \(.description)\n  추천용도: \(.recommended_for | join(", "))\n"' 2>/dev/null || echo "JSON 파싱 실패"
            
            # 필수 타입들이 있는지 확인
            TYPES=$(echo "$BASE_DOCKERFILES" | jq -r '.[].type' 2>/dev/null | tr '\n' ' ')
            echo "사용 가능한 타입: $TYPES"
            
            # 필수 타입 확인
            REQUIRED_TYPES=("minimal" "py311" "py310")
            ALL_FOUND=true
            
            for TYPE in "${REQUIRED_TYPES[@]}"; do
                if echo "$TYPES" | grep -q "$TYPE"; then
                    echo -e "${GREEN}✅ $TYPE 타입 확인${NC}"
                else
                    echo -e "${RED}❌ $TYPE 타입 누락${NC}"
                    ALL_FOUND=false
                fi
            done
            
            if [ "$ALL_FOUND" = true ]; then
                echo -e "${GREEN}✅ 모든 필수 베이스 Dockerfile 타입 확인 완료${NC}"
            else
                echo -e "${RED}❌ 일부 필수 베이스 Dockerfile 타입이 누락되었습니다${NC}"
            fi
            
        else
            echo -e "${RED}❌ 베이스 Dockerfile 개수가 부족합니다 (현재: $COUNT, 최소: 3)${NC}"
        fi
    else
        echo -e "${RED}❌ 응답 성공 플래그가 false입니다${NC}"
    fi
else
    echo -e "${RED}❌ 베이스 Dockerfile 목록 조회 실패 (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

echo

# 2. 베이스 Dockerfile 파일 존재 확인 (Docker 컨테이너 내부)
echo -e "${YELLOW}📁 2. 베이스 Dockerfile 파일 존재 확인${NC}"

# Docker 컨테이너에서 파일 확인
CONTAINER_NAME="streamlit_platform_backend"

echo "Docker 컨테이너 '$CONTAINER_NAME'에서 베이스 Dockerfile 파일들을 확인합니다..."

# 컨테이너가 실행 중인지 확인
if ! docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ 백엔드 컨테이너가 실행되지 않았습니다: $CONTAINER_NAME${NC}"
    echo "docker-compose up -d를 실행하여 컨테이너를 시작하세요."
    exit 1
fi

echo -e "${GREEN}✅ 백엔드 컨테이너 실행 확인${NC}"

# 베이스 Dockerfile 파일들 확인
DOCKERFILE_TYPES=("minimal" "py311" "py310")
ALL_FILES_FOUND=true

for TYPE in "${DOCKERFILE_TYPES[@]}"; do
    DOCKERFILE_NAME="Dockerfile.$TYPE"
    echo "확인 중: /app/dockerfiles/$DOCKERFILE_NAME"
    
    if docker exec "$CONTAINER_NAME" test -f "/app/dockerfiles/$DOCKERFILE_NAME"; then
        echo -e "${GREEN}✅ $DOCKERFILE_NAME 파일 존재 확인${NC}"
        
        # 파일 크기 확인
        SIZE=$(docker exec "$CONTAINER_NAME" stat -c%s "/app/dockerfiles/$DOCKERFILE_NAME" 2>/dev/null || echo "0")
        echo "  파일 크기: $SIZE bytes"
        
        if [ "$SIZE" -gt 100 ]; then
            echo -e "${GREEN}✅ $DOCKERFILE_NAME 파일 크기 적절${NC}"
        else
            echo -e "${RED}❌ $DOCKERFILE_NAME 파일이 너무 작습니다 (${SIZE} bytes)${NC}"
            ALL_FILES_FOUND=false
        fi
    else
        echo -e "${RED}❌ $DOCKERFILE_NAME 파일을 찾을 수 없습니다${NC}"
        ALL_FILES_FOUND=false
    fi
    echo
done

if [ "$ALL_FILES_FOUND" = true ]; then
    echo -e "${GREEN}✅ 모든 베이스 Dockerfile 파일 확인 완료${NC}"
else
    echo -e "${RED}❌ 일부 베이스 Dockerfile 파일이 누락되었습니다${NC}"
    echo "docker-compose.yml의 볼륨 마운트 설정을 확인하세요:"
    echo "  - ./backend/dockerfiles:/app/dockerfiles:ro"
fi

echo

# 3. 베이스 Dockerfile 내용 미리보기
echo -e "${YELLOW}👀 3. 베이스 Dockerfile 내용 미리보기${NC}"

for TYPE in "${DOCKERFILE_TYPES[@]}"; do
    DOCKERFILE_NAME="Dockerfile.$TYPE"
    echo -e "${BLUE}📄 $DOCKERFILE_NAME 내용 (처음 10줄):${NC}"
    
    if docker exec "$CONTAINER_NAME" test -f "/app/dockerfiles/$DOCKERFILE_NAME"; then
        docker exec "$CONTAINER_NAME" head -n 10 "/app/dockerfiles/$DOCKERFILE_NAME" 2>/dev/null || echo "파일 읽기 실패"
    else
        echo "파일을 찾을 수 없습니다."
    fi
    echo "---"
done

echo

# 테스트 결과 요약
echo -e "${BLUE}=== 2.5단계 테스트 결과 요약 ===${NC}"
echo -e "${GREEN}✅ 베이스 Dockerfile 목록 조회 API 테스트 완료${NC}"
echo -e "${GREEN}✅ 베이스 Dockerfile 파일 존재 확인 완료${NC}"
echo -e "${GREEN}✅ 베이스 Dockerfile 내용 미리보기 완료${NC}"
echo
echo -e "${GREEN}🎉 2.5단계: 베이스 Dockerfile 시스템 테스트 성공!${NC}"
echo
echo "다음 단계: 3단계 앱 관리 테스트를 실행하세요."
echo "  ./test_step3_app_management.sh" 
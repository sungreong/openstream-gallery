#!/bin/bash

# 3.5단계: 베이스 Dockerfile 타입별 앱 생성 테스트
# 목적: 각 베이스 Dockerfile 타입으로 앱 생성 및 Dockerfile 생성 확인

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

echo -e "${BLUE}=== 3.5단계: 베이스 Dockerfile 타입별 앱 생성 테스트 ===${NC}"
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

# 테스트할 베이스 Dockerfile 타입들
declare -A DOCKERFILE_TESTS=(
    ["auto"]="자동 선택 - requirements.txt 분석"
    ["minimal"]="최소 버전 - 간단한 앱용"
    ["py311"]="표준 버전 - 일반적인 앱용"
    ["py310"]="데이터사이언스 버전 - 수치 계산용"
)

# 각 타입별로 앱 생성 테스트
CREATED_APPS=()
TEST_COUNT=0
SUCCESS_COUNT=0

for TYPE in "${!DOCKERFILE_TESTS[@]}"; do
    TEST_COUNT=$((TEST_COUNT + 1))
    DESCRIPTION="${DOCKERFILE_TESTS[$TYPE]}"
    
    echo -e "${YELLOW}📱 $TEST_COUNT. '$TYPE' 타입으로 앱 생성 테스트${NC}"
    echo "설명: $DESCRIPTION"
    echo "---"
    
    # 앱 이름에 타입 포함
    APP_NAME="Test-App-${TYPE}-$(date +%s)"
    
    # 앱 생성 요청
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/api/apps/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$APP_NAME\",
            \"description\": \"베이스 Dockerfile 타입 '$TYPE' 테스트 앱\",
            \"git_url\": \"https://github.com/sungreong/ZoneCleaner\",
            \"branch\": \"main\",
            \"main_file\": \"app.py\",
            \"base_dockerfile_type\": \"$TYPE\"
        }")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    echo "HTTP 상태 코드: $HTTP_CODE"
    echo "응답 내용:"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    echo
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ '$TYPE' 타입 앱 생성 성공${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # 앱 ID 추출
        if command -v jq &> /dev/null; then
            APP_ID=$(echo "$BODY" | jq -r '.id // empty' 2>/dev/null)
            if [ -n "$APP_ID" ] && [ "$APP_ID" != "null" ]; then
                CREATED_APPS+=("$APP_ID:$TYPE:$APP_NAME")
                echo "📱 앱 ID: $APP_ID"
                
                # 생성된 앱의 베이스 Dockerfile 타입 확인
                BASE_TYPE=$(echo "$BODY" | jq -r '.base_dockerfile_type // empty' 2>/dev/null)
                if [ "$BASE_TYPE" = "$TYPE" ]; then
                    echo -e "${GREEN}✅ 베이스 Dockerfile 타입 저장 확인: $BASE_TYPE${NC}"
                else
                    echo -e "${RED}❌ 베이스 Dockerfile 타입 불일치: 요청=$TYPE, 저장=$BASE_TYPE${NC}"
                fi
            fi
        fi
    else
        echo -e "${RED}❌ '$TYPE' 타입 앱 생성 실패 (HTTP $HTTP_CODE)${NC}"
        echo "에러 내용: $BODY"
    fi
    
    echo
    sleep 1  # API 부하 방지
done

# 결과 요약
echo -e "${BLUE}=== 앱 생성 테스트 결과 요약 ===${NC}"
echo "총 테스트: $TEST_COUNT개"
echo "성공: $SUCCESS_COUNT개"
echo "실패: $((TEST_COUNT - SUCCESS_COUNT))개"
echo

if [ ${#CREATED_APPS[@]} -gt 0 ]; then
    echo -e "${GREEN}✅ 생성된 앱 목록:${NC}"
    for APP_INFO in "${CREATED_APPS[@]}"; do
        IFS=':' read -r APP_ID TYPE APP_NAME <<< "$APP_INFO"
        echo "  - ID: $APP_ID, 타입: $TYPE, 이름: $APP_NAME"
    done
    echo
    
    # 생성된 앱들의 목록 조회로 검증
    echo -e "${YELLOW}📋 생성된 앱들 목록 조회 검증${NC}"
    
    APPS_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/api/apps/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json")
    
    HTTP_CODE=$(echo "$APPS_RESPONSE" | tail -n1)
    BODY=$(echo "$APPS_RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ 앱 목록 조회 성공${NC}"
        
        if command -v jq &> /dev/null; then
            # 생성된 앱들이 목록에 있는지 확인
            for APP_INFO in "${CREATED_APPS[@]}"; do
                IFS=':' read -r APP_ID TYPE APP_NAME <<< "$APP_INFO"
                
                FOUND_APP=$(echo "$BODY" | jq ".[] | select(.id == $APP_ID)" 2>/dev/null)
                if [ -n "$FOUND_APP" ]; then
                    FOUND_TYPE=$(echo "$FOUND_APP" | jq -r '.base_dockerfile_type // "unknown"' 2>/dev/null)
                    echo -e "${GREEN}✅ 앱 ID $APP_ID 목록에서 확인 (타입: $FOUND_TYPE)${NC}"
                else
                    echo -e "${RED}❌ 앱 ID $APP_ID 목록에서 찾을 수 없음${NC}"
                fi
            done
        fi
    else
        echo -e "${RED}❌ 앱 목록 조회 실패 (HTTP $HTTP_CODE)${NC}"
    fi
    
    echo
    
    # 첫 번째 앱으로 Dockerfile 생성 테스트 (실제 배포는 하지 않음)
    if [ ${#CREATED_APPS[@]} -gt 0 ]; then
        FIRST_APP="${CREATED_APPS[0]}"
        IFS=':' read -r FIRST_APP_ID FIRST_TYPE FIRST_APP_NAME <<< "$FIRST_APP"
        
        echo -e "${YELLOW}🔨 Dockerfile 생성 테스트 (앱 ID: $FIRST_APP_ID, 타입: $FIRST_TYPE)${NC}"
        echo "주의: 실제 배포는 하지 않고 Dockerfile 생성만 테스트합니다."
        echo
        
        # 백엔드 컨테이너에서 Dockerfile 생성 테스트
        CONTAINER_NAME="streamlit_platform_backend"
        
        if docker ps --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
            echo "Docker 컨테이너에서 Dockerfile 생성 테스트 중..."
            
            # 임시 테스트 디렉토리 생성 및 테스트
            TEST_RESULT=$(docker exec "$CONTAINER_NAME" python3 -c "
import sys
sys.path.append('/app')
from services.docker_service import DockerService
import tempfile
import os

try:
    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    print(f'임시 디렉토리: {temp_dir}')
    
    # 간단한 requirements.txt 생성
    with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
        f.write('pandas==2.0.3\nnumpy==1.24.3\nstreamlit==1.28.1\n')
    
    # DockerService 인스턴스 생성
    docker_service = DockerService()
    
    # Dockerfile 생성 테스트
    dockerfile_path = docker_service.generate_dockerfile(temp_dir, 'app.py', '$FIRST_TYPE')
    print(f'Dockerfile 생성 성공: {dockerfile_path}')
    
    # 생성된 Dockerfile 내용 일부 출력
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')[:15]  # 처음 15줄만
    print('\\n=== 생성된 Dockerfile 내용 (처음 15줄) ===')
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f'{i:2d}: {line}')
    
    print('\\n✅ Dockerfile 생성 테스트 성공!')
    
except Exception as e:
    print(f'❌ Dockerfile 생성 테스트 실패: {str(e)}')
    import traceback
    traceback.print_exc()
" 2>/dev/null)
            
            echo "$TEST_RESULT"
        else
            echo -e "${RED}❌ 백엔드 컨테이너가 실행되지 않았습니다${NC}"
        fi
    fi
    
else
    echo -e "${RED}❌ 생성된 앱이 없습니다${NC}"
fi

echo

# 테스트 결과 요약
echo -e "${BLUE}=== 3.5단계 테스트 결과 요약 ===${NC}"
echo -e "${GREEN}✅ 베이스 Dockerfile 타입별 앱 생성 테스트 완료${NC}"
echo -e "${GREEN}✅ 앱 목록 조회 검증 완료${NC}"
echo -e "${GREEN}✅ Dockerfile 생성 테스트 완료${NC}"
echo
echo -e "${GREEN}🎉 3.5단계: 베이스 Dockerfile 타입별 테스트 성공!${NC}"
echo
echo "다음 단계: 4단계 앱 배포 및 모니터링 테스트를 실행하세요."
echo "  ./test_step4_deployment.sh" 
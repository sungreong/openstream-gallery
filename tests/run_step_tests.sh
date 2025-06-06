#!/bin/bash

# 단계별 백엔드 API 테스트 실행 스크립트
# 사용자가 원하는 단계를 선택하여 실행할 수 있습니다.

echo "🚀 Streamlit Platform 백엔드 API 단계별 테스트"
echo "=================================================="
echo ""
echo "📋 테스트 단계:"
echo "  1️⃣  헬스 체크 (서버 연결 확인)"
echo "  2️⃣  사용자 인증 (등록, 로그인, 토큰 검증)"
echo "  2️⃣.5️⃣ 베이스 Dockerfile 시스템 테스트"
echo "  3️⃣  앱 관리 (앱 생성, 목록 조회)"
echo "  3️⃣.5️⃣ 베이스 Dockerfile 타입별 앱 생성 테스트"
echo "  4️⃣  앱 배포 및 모니터링 (Docker 배포, 로그 확인)"
echo "  5️⃣  정리 및 앱 중지 (리소스 정리)"
echo ""
echo "  🔄 기본 테스트 실행 (1-4단계)"
echo "  🧪 확장 테스트 실행 (1-3.5단계 + 베이스 Dockerfile 테스트)"
echo "  🧹 전체 테스트 + 정리 (1-5단계)"
echo "  ❌ 종료"
echo ""

while true; do
    echo -n "실행할 단계를 선택하세요 (1-5, 2.5, 3.5, basic, extended, full, exit): "
    read choice
    
    case $choice in
        1)
            echo ""
            echo "🏥 1단계: 헬스 체크 테스트 실행"
            echo "=================================="
            bash test_step1_health.sh
            ;;
        2)
            echo ""
            echo "🔐 2단계: 사용자 인증 테스트 실행"
            echo "=================================="
            bash test_step2_auth.sh
            ;;
        2.5)
            echo ""
            echo "🐳 2.5단계: 베이스 Dockerfile 시스템 테스트 실행"
            echo "=================================="
            bash test_step2_5_base_dockerfiles.sh
            ;;
        3)
            echo ""
            echo "📱 3단계: 앱 관리 테스트 실행"
            echo "=================================="
            bash test_step3_app_management.sh
            ;;
        3.5)
            echo ""
            echo "🔧 3.5단계: 베이스 Dockerfile 타입별 앱 생성 테스트 실행"
            echo "=================================="
            bash test_step3_5_dockerfile_types.sh
            ;;
        4)
            echo ""
            echo "🚀 4단계: 앱 배포 및 모니터링 테스트 실행"
            echo "=================================="
            bash test_step4_deployment.sh
            ;;
        5)
            echo ""
            echo "🧹 5단계: 정리 및 앱 중지 테스트 실행"
            echo "=================================="
            bash test_step5_cleanup.sh
            ;;
        basic|all)
            echo ""
            echo "🔄 기본 테스트 실행 (1-4단계)"
            echo "=================================="
            echo "⚠️  주의: 각 단계가 순차적으로 실행됩니다."
            echo "실패 시 중단됩니다."
            echo ""
            
            bash test_step1_health.sh && \
            bash test_step2_auth.sh && \
            bash test_step3_app_management.sh && \
            bash test_step4_deployment.sh
            
            if [ $? -eq 0 ]; then
                echo ""
                echo "🎉 기본 테스트가 성공적으로 완료되었습니다!"
                echo "💡 정리를 원하시면 '5' 또는 'full'을 선택하세요."
            else
                echo ""
                echo "❌ 테스트 중 오류가 발생했습니다."
                echo "💡 개별 단계를 실행하여 문제를 확인하세요."
            fi
            ;;
        extended)
            echo ""
            echo "🧪 확장 테스트 실행 (1-3.5단계 + 베이스 Dockerfile 테스트)"
            echo "=================================="
            echo "⚠️  주의: 베이스 Dockerfile 시스템을 포함한 확장 테스트입니다."
            echo "실패 시 중단됩니다."
            echo ""
            
            bash test_step1_health.sh && \
            bash test_step2_auth.sh && \
            bash test_step2_5_base_dockerfiles.sh && \
            bash test_step3_app_management.sh && \
            bash test_step3_5_dockerfile_types.sh
            
            if [ $? -eq 0 ]; then
                echo ""
                echo "🎉 확장 테스트가 성공적으로 완료되었습니다!"
                echo "💡 배포 테스트를 원하시면 '4'를, 정리를 원하시면 'full'을 선택하세요."
            else
                echo ""
                echo "❌ 테스트 중 오류가 발생했습니다."
                echo "💡 개별 단계를 실행하여 문제를 확인하세요."
            fi
            ;;
        full)
            echo ""
            echo "🧹 전체 테스트 + 정리 실행 (1-5단계)"
            echo "=================================="
            echo "⚠️  주의: 모든 단계가 순차적으로 실행되고 마지막에 정리됩니다."
            echo ""
            
            bash test_step1_health.sh && \
            bash test_step2_auth.sh && \
            bash test_step3_app_management.sh && \
            bash test_step4_deployment.sh && \
            bash test_step5_cleanup.sh
            
            if [ $? -eq 0 ]; then
                echo ""
                echo "🎉 전체 테스트 및 정리가 성공적으로 완료되었습니다!"
            else
                echo ""
                echo "❌ 테스트 중 오류가 발생했습니다."
            fi
            ;;
        exit|quit|q)
            echo ""
            echo "👋 테스트를 종료합니다."
            exit 0
            ;;
        *)
            echo "❌ 잘못된 선택입니다. 1-5, 2.5, 3.5, basic, extended, full, exit 중 하나를 입력하세요."
            ;;
    esac
    
    echo ""
    echo "=================================================="
    echo ""
done 
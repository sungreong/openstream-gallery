#!/usr/bin/env python3
"""
베이스 이미지 빌드 스크립트
Streamlit 플랫폼에서 사용할 베이스 이미지들을 미리 빌드합니다.
"""

import sys
import os
import logging
import asyncio
from services.base_image_manager import BaseImageManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("base_image_build.log")],
)

logger = logging.getLogger(__name__)


async def main():
    """메인 함수"""
    logger.info("🚀 베이스 이미지 빌드 시작")

    try:
        # BaseImageManager 초기화
        manager = BaseImageManager()

        # 모든 베이스 이미지 정보 가져오기
        base_images = manager.get_all_base_images()

        logger.info(f"📋 빌드할 베이스 이미지: {len(base_images)}개")
        for image_type, info in base_images.items():
            logger.info(f"  - {image_type}: {info['description']}")

        # 각 베이스 이미지 빌드
        success_count = 0
        failed_images = []

        for image_type, info in base_images.items():
            logger.info(f"\n🔨 '{image_type}' 베이스 이미지 빌드 시작...")

            try:
                # 이미지가 이미 존재하는지 확인
                if manager.check_base_image_exists(image_type):
                    logger.info(f"✅ '{image_type}' 이미지가 이미 존재합니다. 스킵.")
                    success_count += 1
                    continue

                # 베이스 이미지 빌드
                if manager.build_base_image(image_type):
                    logger.info(f"✅ '{image_type}' 베이스 이미지 빌드 성공!")
                    success_count += 1
                else:
                    logger.error(f"❌ '{image_type}' 베이스 이미지 빌드 실패")
                    failed_images.append(image_type)

            except Exception as e:
                logger.error(f"❌ '{image_type}' 베이스 이미지 빌드 중 에러: {str(e)}")
                failed_images.append(image_type)

        # 결과 요약
        logger.info(f"\n📊 베이스 이미지 빌드 완료")
        logger.info(f"✅ 성공: {success_count}개")
        logger.info(f"❌ 실패: {len(failed_images)}개")

        if failed_images:
            logger.error(f"실패한 이미지: {', '.join(failed_images)}")
            return 1
        else:
            logger.info("🎉 모든 베이스 이미지 빌드 성공!")
            return 0

    except Exception as e:
        logger.error(f"💥 베이스 이미지 빌드 중 치명적 에러: {str(e)}")
        return 1


def build_specific_image(image_type: str):
    """특정 베이스 이미지만 빌드"""
    logger.info(f"🎯 특정 베이스 이미지 빌드: {image_type}")

    try:
        manager = BaseImageManager()

        if image_type not in manager.get_all_base_images():
            logger.error(f"❌ 알 수 없는 이미지 타입: {image_type}")
            logger.info(f"사용 가능한 타입: {', '.join(manager.get_all_base_images().keys())}")
            return 1

        if manager.build_base_image(image_type):
            logger.info(f"✅ '{image_type}' 베이스 이미지 빌드 성공!")
            return 0
        else:
            logger.error(f"❌ '{image_type}' 베이스 이미지 빌드 실패")
            return 1

    except Exception as e:
        logger.error(f"💥 베이스 이미지 빌드 중 에러: {str(e)}")
        return 1


def cleanup_old_images():
    """오래된 베이스 이미지 정리"""
    logger.info("🧹 오래된 베이스 이미지 정리 시작")

    try:
        manager = BaseImageManager()
        manager.cleanup_old_images(keep_latest=2)
        logger.info("✅ 베이스 이미지 정리 완료")
        return 0
    except Exception as e:
        logger.error(f"💥 베이스 이미지 정리 중 에러: {str(e)}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "build":
            if len(sys.argv) > 2:
                # 특정 이미지 빌드
                image_type = sys.argv[2]
                exit_code = build_specific_image(image_type)
            else:
                # 모든 이미지 빌드
                exit_code = asyncio.run(main())
        elif command == "cleanup":
            # 오래된 이미지 정리
            exit_code = cleanup_old_images()
        elif command == "help":
            print("베이스 이미지 빌드 스크립트")
            print("사용법:")
            print("  python build_base_images.py build          # 모든 베이스 이미지 빌드")
            print("  python build_base_images.py build minimal  # 특정 베이스 이미지 빌드")
            print("  python build_base_images.py cleanup        # 오래된 이미지 정리")
            print("  python build_base_images.py help           # 도움말")
            print()
            print("사용 가능한 베이스 이미지 타입:")
            try:
                manager = BaseImageManager()
                for image_type, info in manager.get_all_base_images().items():
                    print(f"  - {image_type}: {info['description']}")
            except:
                print("  - minimal: 최소 의존성 베이스 이미지")
                print("  - standard: 표준 Python 3.11 베이스 이미지")
                print("  - datascience: 데이터사이언스용 베이스 이미지")
            exit_code = 0
        else:
            print(f"알 수 없는 명령어: {command}")
            print("사용법: python build_base_images.py [build|cleanup|help]")
            exit_code = 1
    else:
        # 기본: 모든 이미지 빌드
        exit_code = asyncio.run(main())

    sys.exit(exit_code)

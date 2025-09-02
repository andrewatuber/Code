#!/usr/bin/env python3
"""
Virtual Fitting Backend Server
가상 피팅 백엔드 서버 실행 스크립트
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Python 버전 확인"""
    version = sys.version_info
    if version.major != 3 or version.minor < 8:
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: Python {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} 확인됨")
    return True

def check_dependencies():
    """필수 의존성 확인"""
    try:
        import fastapi
        import uvicorn
        import cv2
        import mediapipe
        import numpy
        print("✅ 모든 필수 의존성이 설치되어 있습니다.")
        return True
    except ImportError as e:
        print(f"❌ 의존성 누락: {e}")
        print("다음 명령어로 설치하세요:")
        print("pip3 install -r requirements.txt")
        print("또는:")
        print("pip install -r requirements.txt")
        return False

def create_directories():
    """필요한 디렉토리 생성"""
    directories = ['uploads/models', 'uploads/clothes', 'results']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 디렉토리 생성: {directory}")

def main():
    """메인 실행 함수"""
    print("🚀 Virtual Fitting Backend Server 시작")
    print("=" * 50)
    
    # Python 버전 확인
    if not check_python_version():
        sys.exit(1)
    
    # 의존성 확인
    if not check_dependencies():
        print("\n설치 명령어:")
        print("pip3 install -r requirements.txt")
        print("또는:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # 디렉토리 생성
    create_directories()
    
    # 서버 실행
    print("\n🌐 서버를 시작합니다...")
    print("📍 URL: http://localhost:8000")
    print("📚 API 문서: http://localhost:8000/docs")
    print("⏹️  종료하려면 Ctrl+C를 누르세요")
    print("=" * 50)
    
    try:
        # uvicorn으로 서버 실행
        os.system("uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    except KeyboardInterrupt:
        print("\n👋 서버가 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 서버 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/bin/bash

echo "🚀 Virtual Fitting 백엔드 서버 시작"
echo "=================================="

cd backend

# Python 3 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3가 설치되어 있지 않습니다."
    exit 1
fi

echo "✅ Python 버전: $(python3 --version)"

# 필요한 디렉토리 생성
mkdir -p uploads/models uploads/clothes results

# 서버 시작
echo "🔧 백엔드 서버를 시작합니다..."
echo "📍 URL: http://localhost:8000"
echo "📚 API 문서: http://localhost:8000/docs"
echo "⏹️  종료하려면 Ctrl+C를 누르세요"
echo "=================================="

# Python 모듈로 직접 실행
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
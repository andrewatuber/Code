#!/bin/bash

# Virtual Fitting Frontend Client 시작 스크립트

echo "🚀 Virtual Fitting Frontend Client 시작"
echo "=================================================="

# Node.js 버전 확인
if ! command -v node &> /dev/null; then
    echo "❌ Node.js가 설치되어 있지 않습니다."
    echo "https://nodejs.org 에서 Node.js를 설치하세요."
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION 확인됨"

# npm 버전 확인
if ! command -v npm &> /dev/null; then
    echo "❌ npm이 설치되어 있지 않습니다."
    exit 1
fi

NPM_VERSION=$(npm --version)
echo "✅ npm $NPM_VERSION 확인됨"

# package.json 존재 확인
if [ ! -f "package.json" ]; then
    echo "❌ package.json 파일이 없습니다."
    echo "frontend 디렉토리에서 실행하세요."
    exit 1
fi

# node_modules 확인 및 설치
if [ ! -d "node_modules" ]; then
    echo "📦 의존성 설치 중..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 의존성 설치 실패"
        echo "다음 명령어를 수동으로 실행하세요:"
        echo "npm cache clean --force"
        echo "npm install"
        exit 1
    fi
else
    echo "✅ 의존성이 이미 설치되어 있습니다."
fi

# 백엔드 서버 확인
echo "🔍 백엔드 서버 연결 확인 중..."
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ 백엔드 서버가 실행 중입니다."
else
    echo "⚠️  백엔드 서버가 실행되고 있지 않습니다."
    echo "backend 디렉토리에서 다음 명령어를 실행하세요:"
    echo "python start_server.py"
    echo ""
    echo "그래도 프론트엔드를 시작하시겠습니까? (y/n)"
    read -r response
    if [[ ! $response =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 개발 서버 시작
echo ""
echo "🌐 프론트엔드 서버를 시작합니다..."
echo "📍 URL: http://localhost:3000"
echo "⏹️  종료하려면 Ctrl+C를 누르세요"
echo "=================================================="

npm start
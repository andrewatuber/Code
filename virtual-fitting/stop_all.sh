#!/bin/bash

# Virtual Fitting 모든 서비스 종료 스크립트

echo "🛑 Virtual Fitting 모든 서비스 종료 중..."
echo "=================================================="

# 프론트엔드 종료
echo "🎨 프론트엔드 종료 중..."
FRONTEND_PID=$(lsof -ti:3000)
if [ ! -z "$FRONTEND_PID" ]; then
    echo "📍 프론트엔드 프로세스 ID: $FRONTEND_PID"
    kill $FRONTEND_PID
    sleep 2
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️  강제 종료 중..."
        kill -9 $FRONTEND_PID
    fi
    echo "✅ 프론트엔드 종료 완료"
else
    echo "ℹ️  실행 중인 프론트엔드가 없습니다."
fi

echo ""

# 백엔드 종료
echo "🔧 백엔드 종료 중..."
BACKEND_PID=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PID" ]; then
    echo "📍 백엔드 프로세스 ID: $BACKEND_PID"
    kill $BACKEND_PID
    sleep 2
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "⚠️  강제 종료 중..."
        kill -9 $BACKEND_PID
    fi
    echo "✅ 백엔드 종료 완료"
else
    echo "ℹ️  실행 중인 백엔드가 없습니다."
fi

echo ""

# 추가 포트 확인 (혹시 다른 포트에서 실행 중인 경우)
echo "🔍 추가 포트 확인 중..."
ADDITIONAL_PORTS=$(lsof -ti:3001,3002,8001,8002,8080,9000 2>/dev/null)
if [ ! -z "$ADDITIONAL_PORTS" ]; then
    echo "⚠️  추가 포트에서 실행 중인 프로세스 발견:"
    for port in 3001 3002 8001 8002 8080 9000; do
        pid=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pid" ]; then
            echo "   포트 $port: 프로세스 ID $pid"
            kill $pid 2>/dev/null
        fi
    done
else
    echo "ℹ️  추가 포트에서 실행 중인 프로세스가 없습니다."
fi

echo ""
echo "=================================================="
echo "🎉 모든 Virtual Fitting 서비스가 종료되었습니다!"
echo ""
echo "📋 실행 중인 프로세스 확인:"
echo "   프론트엔드 (포트 3000): $(lsof -ti:3000 2>/dev/null || echo '없음')"
echo "   백엔드 (포트 8000): $(lsof -ti:8000 2>/dev/null || echo '없음')"


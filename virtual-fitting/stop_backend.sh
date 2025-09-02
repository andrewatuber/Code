#!/bin/bash

# Virtual Fitting Backend 종료 스크립트

echo "🛑 Virtual Fitting Backend 종료 중..."
echo "=================================================="

# 포트 8000에서 실행 중인 프로세스 찾기
BACKEND_PID=$(lsof -ti:8000)

if [ -z "$BACKEND_PID" ]; then
    echo "❌ 포트 8000에서 실행 중인 백엔드 프로세스가 없습니다."
    exit 0
fi

echo "📍 실행 중인 백엔드 프로세스 ID: $BACKEND_PID"

# 프로세스 정보 표시
echo "📊 프로세스 정보:"
ps -p $BACKEND_PID -o pid,ppid,cmd,etime

# 프로세스 종료
echo ""
echo "🔴 프로세스를 종료합니다..."
kill $BACKEND_PID

# 종료 확인
sleep 2
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "⚠️  프로세스가 아직 실행 중입니다. 강제 종료합니다..."
    kill -9 $BACKEND_PID
    sleep 1
fi

# 최종 확인
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ 백엔드 프로세스가 성공적으로 종료되었습니다."
else
    echo "❌ 프로세스 종료에 실패했습니다."
    exit 1
fi

echo "=================================================="
echo "👋 Virtual Fitting Backend가 종료되었습니다."

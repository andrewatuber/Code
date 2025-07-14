#!/bin/bash

echo "🎮 한국 마작 게임 빌드 시작..."

# 기존 빌드 파일 정리
echo "📁 기존 빌드 파일 정리..."
rm -rf build/
rm -rf dist/
rm -f Korean_Mahjong_Mac.zip

# 의존성 확인
echo "📦 의존성 확인..."
python3 -c "import pygame; print('pygame 설치 확인 ✅')" || {
    echo "❌ pygame이 설치되지 않았습니다. python3 -m pip install pygame --break-system-packages 실행하세요."
    exit 1
}

python3 -c "import PyInstaller; print('PyInstaller 설치 확인 ✅')" || {
    echo "❌ PyInstaller가 설치되지 않았습니다. python3 -m pip install pyinstaller --break-system-packages 실행하세요."
    exit 1
}

# PyInstaller로 빌드
echo "🔨 PyInstaller로 빌드 중..."
python3 -m PyInstaller mahjong.spec --clean --noconfirm

# 빌드 결과 확인
if [ -f "dist/Korean_Mahjong" ]; then
    echo "✅ 실행 파일 생성 완료: dist/Korean_Mahjong"
    echo "📊 파일 크기: $(du -h dist/Korean_Mahjong | cut -f1)"
else
    echo "❌ 실행 파일 생성 실패"
    exit 1
fi

if [ -d "dist/Korean_Mahjong.app" ]; then
    echo "✅ Mac 앱 번들 생성 완료: dist/Korean_Mahjong.app"
    echo "📊 앱 번들 크기: $(du -sh dist/Korean_Mahjong.app | cut -f1)"
else
    echo "❌ Mac 앱 번들 생성 실패"
    exit 1
fi

# ZIP 파일 생성
echo "📦 배포용 ZIP 파일 생성 중..."
cd dist/
zip -r Korean_Mahjong_Mac.zip Korean_Mahjong Korean_Mahjong.app
cd ..

if [ -f "dist/Korean_Mahjong_Mac.zip" ]; then
    echo "✅ ZIP 파일 생성 완료: dist/Korean_Mahjong_Mac.zip"
    echo "📊 ZIP 파일 크기: $(du -h dist/Korean_Mahjong_Mac.zip | cut -f1)"
else
    echo "❌ ZIP 파일 생성 실패"
    exit 1
fi

echo ""
echo "🎉 빌드 완료!"
echo "📁 생성된 파일:"
echo "   - dist/Korean_Mahjong (실행 파일)"
echo "   - dist/Korean_Mahjong.app (Mac 앱 번들)"
echo "   - dist/Korean_Mahjong_Mac.zip (배포용 ZIP)"
echo ""
echo "🚀 실행 방법:"
echo "   ./dist/Korean_Mahjong"
echo "   또는 Korean_Mahjong.app을 더블클릭" 
@echo off
echo 🎮 한국 마작 게임 빌드 시작...

rem 기존 빌드 파일 정리
echo 📁 기존 빌드 파일 정리...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

rem 의존성 확인
echo 📦 의존성 확인...
python -c "import pygame; print('pygame 설치 확인 ✅')" || (
    echo ❌ pygame이 설치되지 않았습니다. pip install pygame 실행하세요.
    pause
    exit /b 1
)

python -c "import PyInstaller; print('PyInstaller 설치 확인 ✅')" || (
    echo ❌ PyInstaller가 설치되지 않았습니다. pip install pyinstaller 실행하세요.
    pause
    exit /b 1
)

rem 윈도우용 실행 파일 빌드
echo 🪟 윈도우용 실행 파일 빌드 중...
pyinstaller mahjong_windows.spec

if %errorlevel% equ 0 (
    echo ✅ 윈도우용 빌드 완료!
    echo 📂 생성된 파일:
    echo    - dist/Korean_Mahjong.exe (윈도우용 실행 파일)
    
    rem 파일 크기 확인
    echo 📊 파일 크기:
    dir dist\Korean_Mahjong.exe
    
    echo.
    echo 🎯 실행 방법:
    echo    1. dist/Korean_Mahjong.exe 더블클릭
    echo.
    echo 🎮 게임을 즐기세요!
) else (
    echo ❌ 빌드 실패!
    pause
    exit /b 1
)

pause 
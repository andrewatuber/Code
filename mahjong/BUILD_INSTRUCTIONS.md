# 한국 마작 게임 - 실행 파일 빌드 가이드

## 📦 실행 파일 생성하기

### 1. 필요한 패키지 설치

```bash
pip install pyinstaller pygame
```

### 2. 맥용 실행 파일 생성

```bash
pyinstaller mahjong.spec
```

생성된 파일:
- `dist/Korean_Mahjong.app` - 맥용 앱 번들
- `dist/Korean_Mahjong` - 맥용 실행 파일

### 3. 윈도우용 실행 파일 생성 (윈도우에서 실행)

```bash
pyinstaller mahjong_windows.spec
```

생성된 파일:
- `dist/Korean_Mahjong.exe` - 윈도우용 실행 파일

## 🎮 게임 실행하기

### 맥에서 실행:
1. `Korean_Mahjong.app`을 더블클릭하거나
2. 터미널에서 `./dist/Korean_Mahjong` 실행

### 윈도우에서 실행:
1. `Korean_Mahjong.exe`를 더블클릭

## 📋 포함된 파일들

실행 파일에는 다음 파일들이 자동으로 포함됩니다:
- 모든 Python 소스 파일 (*.py)
- 타일 이미지 파일들 (tiles/*.png)
- 클릭 사운드 파일 (click.wav)
- 필요한 Python 라이브러리들

## 🔧 문제 해결

### 게임이 실행되지 않는 경우:
1. 터미널에서 실행하여 오류 메시지 확인
2. pygame이 제대로 설치되었는지 확인
3. 모든 리소스 파일이 포함되었는지 확인

### 맥에서 보안 경고가 나타나는 경우:
1. 시스템 환경설정 > 보안 및 개인정보 보호
2. "확인되지 않은 개발자" 앱 실행 허용

## 🎯 게임 조작법

- **마우스 클릭**: 패 선택 및 버리기
- **액션 버튼**: 펑, 깡, 론, 리치 등
- **패스**: 액션을 하지 않고 넘어가기

## 📈 게임 규칙

- 한국 마작 규칙 적용
- 4인 플레이 (플레이어 1명 + AI 3명)
- 총 12판 게임
- 점수 계산: 론 5점, 쯔모 10점, 멘젠 깨진 상태 2점

즐거운 게임 되세요! 🀄️ 
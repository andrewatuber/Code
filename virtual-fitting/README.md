# Virtual Fitting - AI 기반 가상 피팅 웹앱

이 프로젝트는 AI를 활용한 가상 피팅 서비스입니다. 사용자의 전신 사진과 키를 업로드하면 신체 치수를 자동으로 계산하고, 옷의 사진과 사이즈 정보를 입력하면 가상으로 피팅한 결과를 보여줍니다.

## 🎯 주요 기능

### AI 신체 측정
- MediaPipe를 활용한 정확한 신체 치수 계산
- 포즈 감지를 통한 신체 부위 자동 인식

### 옷 분석
- 이미지 분석을 통한 옷 종류 및 치수 자동 감지
- 옷 종류별 맞춤형 분석 (상의, 하의, 원피스 등)

### 현실적인 가상 피팅
- **MediaPipe 포즈 감지를 통한 정확한 신체 부위 매핑**
- **옷 종류별 맞춤형 피팅 알고리즘**
- **자연스러운 이미지 블렌딩 및 합성**
- **실시간 피팅 상태 분석 및 추천**

### 실시간 미리보기
- 피팅 전 예상 결과 확인
- 신체와 옷 사이즈 비교 분석

### 데이터 저장
- 업로드한 모델과 옷 정보 재사용 가능
- 피팅 결과 이미지 및 분석 데이터 저장

## 기술 스택

### 백엔드
- **Python 3.8+**
- **FastAPI** - REST API 서버
- **MediaPipe** - 포즈 감지 및 신체 측정
- **OpenCV** - 이미지 처리
- **NumPy** - 수치 계산

### 프론트엔드
- **React 18** - 사용자 인터페이스
- **Axios** - HTTP 클라이언트
- **React Dropzone** - 파일 업로드
- **Styled Components** - 스타일링

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone <repository-url>
cd virtual-fitting
```

### 2. 백엔드 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (두 가지 방법 중 선택)
# 방법 1: 직접 실행
python main.py

# 방법 2: start_server.py 사용
python start_server.py
```

백엔드 서버는 `http://localhost:8000`에서 실행됩니다.

### 3. 프론트엔드 실행

새 터미널에서:

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm start
```

프론트엔드는 `http://localhost:3000`에서 실행됩니다.

## 📁 실행 스크립트

프로젝트에는 다음과 같은 실행 스크립트가 제공됩니다:

### 🚀 시작 스크립트
- **`start_backend.sh`**: 백엔드 서버만 실행 (Linux/macOS)
- **`frontend/start_client.sh`**: 프론트엔드만 실행 (Linux/macOS)

### 🛑 종료 스크립트
- **`stop_frontend.sh`**: 프론트엔드 서버만 종료 (Linux/macOS)
- **`stop_backend.sh`**: 백엔드 서버만 종료 (Linux/macOS)
- **`stop_all.sh`**: 모든 서비스를 한 번에 종료 (Linux/macOS)

### 스크립트 사용법

```bash
# 백엔드만 실행
./start_backend.sh

# 프론트엔드만 실행 (새 터미널에서)
cd frontend
./start_client.sh

# 프론트엔드만 종료
./stop_frontend.sh

# 백엔드만 종료
./stop_backend.sh

# 모든 서비스 종료
./stop_all.sh
```

## 🌐 접속 URL

- **웹앱**: http://localhost:3000
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 사용 방법

### 1단계: 모델 업로드
1. 전신이 잘 보이는 사진을 업로드합니다
2. 키(cm)를 입력합니다
3. "신체 치수 계산" 버튼을 클릭합니다
4. AI가 자동으로 신체 각 부위의 치수를 계산합니다

### 2단계: 옷 업로드
1. 피팅하고 싶은 옷의 사진을 업로드합니다
2. **옷 종류를 선택합니다 (상의, 하의, 원피스, 자켓, 니트 등)**
3. 다음 중 하나의 방법으로 사이즈 정보를 입력합니다:
   - **치수 직접 입력**: 폭, 길이 등을 cm 단위로 입력
   - **사이즈 차트 입력**: 상세한 사이즈 정보를 텍스트나 JSON 형식으로 입력
4. "옷 치수 분석" 버튼을 클릭합니다

### 3단계: 가상 피팅
1. 선택한 모델과 옷의 정보를 확인합니다
2. **AI가 옷 종류에 따라 적절한 피팅 알고리즘을 선택합니다**
3. **MediaPipe 포즈 감지를 통해 정확한 신체 부위에 옷을 배치합니다**
4. 예상 피팅 결과를 미리 볼 수 있습니다
5. "가상 피팅 생성" 버튼을 클릭합니다
6. **AI가 현실적인 가상 피팅 이미지를 생성합니다**

### 4단계: 결과 확인
1. 생성된 가상 피팅 이미지를 확인합니다
2. 피팅 상태와 추천사항을 확인합니다
3. 새로운 피팅을 시작하거나 다른 옷으로 피팅할 수 있습니다

## API 엔드포인트

### 모델 관련
- `POST /api/upload-model` - 모델 이미지와 키 업로드
- `GET /api/models` - 저장된 모델 목록 조회

### 옷 관련
- `POST /api/upload-clothing` - 옷 이미지와 사이즈 정보 업로드
- `GET /api/clothes` - 저장된 옷 목록 조회

### 가상 피팅
- `POST /api/virtual-fitting` - 가상 피팅 이미지 생성
- `GET /api/result/{filename}` - 결과 이미지 조회

## 디렉토리 구조

```
virtual-fitting/
├── backend/                 # 백엔드 (Python/FastAPI)
│   ├── main.py             # 메인 API 서버
│   ├── start_server.py     # 서버 실행 스크립트
│   ├── body_measurement.py # 신체 치수 계산 모듈
│   ├── clothing_analysis.py# 옷 분석 모듈
│   ├── virtual_fitting.py  # 가상 피팅 모듈
│   ├── requirements.txt    # Python 의존성
│   ├── uploads/           # 업로드된 파일
│   └── results/           # 생성된 결과 이미지
├── frontend/               # 프론트엔드 (React)
│   ├── public/
│   ├── src/
│   │   ├── components/    # React 컴포넌트
│   │   ├── services/      # API 서비스
│   │   └── App.js        # 메인 앱 컴포넌트
│   ├── package.json      # Node.js 의존성
│   └── start_client.sh   # 프론트엔드 실행 스크립트
├── start_backend.sh       # 백엔드 실행 스크립트
├── stop_frontend.sh       # 프론트엔드 종료 스크립트
├── stop_backend.sh        # 백엔드 종료 스크립트
├── stop_all.sh           # 모든 서비스 종료 스크립트
└── README.md             # 이 파일
```

## 🧪 테스트

### 가상 피팅 기능 테스트
```bash
# 백엔드 디렉토리에서
cd backend
python ../test_virtual_fitting.py
```

이 테스트는 간단한 테스트 이미지를 생성하여 가상 피팅 기능이 정상적으로 작동하는지 확인합니다.

## 주의사항

1. **이미지 품질**: 신체 치수 계산의 정확도를 위해 전신이 명확히 보이는 고품질 이미지를 사용하세요.

2. **포즈**: 정면을 바라보고 팔과 다리가 벌어진 자세의 사진이 가장 좋습니다.

3. **배경**: 단순한 배경의 이미지가 더 정확한 결과를 제공합니다.

4. **옷 사진**: 옷이 평평하게 펼쳐진 상태의 사진이 분석에 적합합니다.

## 문제 해결

### 백엔드 관련
- **MediaPipe 설치 오류**: Python 3.8-3.11 버전을 사용하세요.
- **포트 충돌**: `main.py`에서 포트 번호를 변경할 수 있습니다.

### 프론트엔드 관련
- **npm 설치 오류**: Node.js 16+ 버전을 사용하세요.
- **CORS 오류**: 백엔드가 먼저 실행되고 있는지 확인하세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해 주세요. Pull Request도 환영합니다!
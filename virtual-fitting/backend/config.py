"""
Virtual Fitting Backend Configuration
백엔드 설정 관리 모듈
"""

import os
from typing import List

class Settings:
    """애플리케이션 설정 클래스"""
    
    # 서버 설정
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["jpg", "jpeg", "png", "bmp"]
    
    # 디렉토리 설정
    UPLOAD_DIR: str = "uploads"
    MODELS_DIR: str = os.path.join(UPLOAD_DIR, "models")
    CLOTHES_DIR: str = os.path.join(UPLOAD_DIR, "clothes")
    RESULTS_DIR: str = "results"
    
    # MediaPipe 설정
    POSE_MODEL_COMPLEXITY: int = 2
    POSE_MIN_DETECTION_CONFIDENCE: float = 0.5
    POSE_MIN_TRACKING_CONFIDENCE: float = 0.5
    
    # 이미지 처리 설정
    MAX_IMAGE_WIDTH: int = 1024
    MAX_IMAGE_HEIGHT: int = 1024
    JPEG_QUALITY: int = 85
    
    # 가상 피팅 설정
    FIT_TOLERANCE: float = 0.1  # 10% 여유
    BLEND_ALPHA: float = 0.7    # 이미지 블렌딩 투명도
    
    # 신체 측정 기본 비율
    BODY_RATIOS = {
        "chest_to_shoulder": 1.4,
        "waist_to_shoulder": 1.2,
        "hip_to_shoulder": 1.5,
        "arm_to_shoulder": 1.8,
        "leg_to_height": 0.45
    }
    
    # 옷 종류별 기본 비율
    CLOTHING_RATIOS = {
        "shirt": {
            "chest_to_width": 1.0,
            "length_to_width": 1.3,
            "shoulder_to_width": 0.8,
            "sleeve_to_width": 0.7,
            "neck_to_width": 0.3
        },
        "pants": {
            "waist_to_width": 1.0,
            "hip_to_width": 1.1,
            "length_to_width": 2.5,
            "thigh_to_width": 0.6,
            "calf_to_width": 0.4
        },
        "dress": {
            "chest_to_width": 1.0,
            "waist_to_width": 0.8,
            "hip_to_width": 1.1,
            "length_to_width": 2.0,
            "shoulder_to_width": 0.8
        },
        "jacket": {
            "chest_to_width": 1.0,
            "length_to_width": 1.2,
            "shoulder_to_width": 0.9,
            "sleeve_to_width": 0.8,
            "neck_to_width": 0.35
        }
    }

# 전역 설정 인스턴스
settings = Settings()

def create_directories():
    """필요한 디렉토리들을 생성합니다."""
    directories = [
        settings.UPLOAD_DIR,
        settings.MODELS_DIR,
        settings.CLOTHES_DIR,
        settings.RESULTS_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
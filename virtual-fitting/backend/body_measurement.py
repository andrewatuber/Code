import cv2
import numpy as np
from typing import Dict, Tuple, Optional
import math

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️  MediaPipe를 사용할 수 없습니다. 기본 측정 방식을 사용합니다.")

class BodyMeasurement:
    def __init__(self):
        if MEDIAPIPE_AVAILABLE:
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=2,
                enable_segmentation=True,
                min_detection_confidence=0.5
            )
            self.mp_drawing = mp.solutions.drawing_utils
        else:
            self.mp_pose = None
            self.pose = None
            self.mp_drawing = None
    
    def calculate_measurements(self, image_path: str, height_cm: float) -> Dict[str, float]:
        """이미지에서 신체 치수를 계산합니다."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("이미지를 불러올 수 없습니다.")
        
        if MEDIAPIPE_AVAILABLE and self.pose:
            return self._calculate_with_mediapipe(image, height_cm)
        else:
            return self._calculate_with_basic_method(image, height_cm)
    
    def _calculate_with_mediapipe(self, image: np.ndarray, height_cm: float) -> Dict[str, float]:
        """MediaPipe를 사용한 정확한 측정"""
        # RGB로 변환
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # MediaPipe로 포즈 감지
        results = self.pose.process(image_rgb)
        
        if not results.pose_landmarks:
            # MediaPipe가 실패하면 기본 방법 사용
            return self._calculate_with_basic_method(image, height_cm)
        
        # 랜드마크 좌표 추출
        landmarks = results.pose_landmarks.landmark
        h, w = image.shape[:2]
        
        # 픽셀 좌표로 변환
        points = {}
        for i, landmark in enumerate(landmarks):
            points[i] = (int(landmark.x * w), int(landmark.y * h))
        
        # 픽셀 대 실제 비율 계산 (키를 기준으로)
        pixel_height = self._calculate_body_height_pixels(points)
        pixel_to_cm_ratio = height_cm / pixel_height if pixel_height > 0 else height_cm / h
        
        # 각 부위별 치수 계산
        measurements = self._calculate_body_parts(points, pixel_to_cm_ratio)
        
        return measurements
    
    def _calculate_with_basic_method(self, image: np.ndarray, height_cm: float) -> Dict[str, float]:
        """기본 이미지 분석을 통한 추정 측정"""
        h, w = image.shape[:2]
        
        # 키를 기준으로 한 비례 계산
        # 일반적인 인체 비율을 사용하여 추정
        measurements = {
            "shoulder_width": round(height_cm * 0.25, 1),      # 키의 25%
            "chest_circumference": round(height_cm * 0.55, 1), # 키의 55%
            "waist_circumference": round(height_cm * 0.45, 1), # 키의 45%
            "hip_circumference": round(height_cm * 0.58, 1),   # 키의 58%
            "arm_length": round(height_cm * 0.44, 1),          # 키의 44%
            "leg_length": round(height_cm * 0.52, 1),          # 키의 52%
            "torso_length": round(height_cm * 0.48, 1),        # 키의 48%
            "neck_circumference": round(height_cm * 0.20, 1)   # 키의 20%
        }
        
        return measurements
    
    def _calculate_body_height_pixels(self, points: Dict[int, Tuple[int, int]]) -> float:
        """픽셀 단위의 신체 높이 계산"""
        if not points:
            return 0
        
        try:
            # 머리 꼭대기에서 발끝까지의 거리
            nose = points.get(0)  # 코
            left_ankle = points.get(27)  # 왼쪽 발목
            right_ankle = points.get(28)  # 오른쪽 발목
            
            if not all([nose, left_ankle, right_ankle]):
                return 0
            
            # 발목 중점
            ankle_center = (
                (left_ankle[0] + right_ankle[0]) / 2,
                (left_ankle[1] + right_ankle[1]) / 2
            )
            
            # 머리에서 발목까지의 거리
            height_pixels = math.sqrt(
                (nose[0] - ankle_center[0]) ** 2 + 
                (nose[1] - ankle_center[1]) ** 2
            )
            
            return height_pixels
        except (KeyError, TypeError):
            return 0
    
    def _calculate_body_parts(self, points: Dict[int, Tuple[int, int]], ratio: float) -> Dict[str, float]:
        """각 신체 부위별 치수 계산"""
        measurements = {}
        
        try:
            # 어깨 너비
            left_shoulder = points.get(11)
            right_shoulder = points.get(12)
            if left_shoulder and right_shoulder:
                shoulder_width = self._distance(left_shoulder, right_shoulder) * ratio
                measurements["shoulder_width"] = round(shoulder_width, 1)
            else:
                measurements["shoulder_width"] = round(170 * 0.25, 1)  # 기본값
            
            # 가슴 둘레 (어깨 너비 기준으로 추정)
            chest_circumference = measurements["shoulder_width"] * 2.2
            measurements["chest_circumference"] = round(chest_circumference, 1)
            
            # 허리 둘레
            left_hip = points.get(23)
            right_hip = points.get(24)
            if left_hip and right_hip:
                hip_width = self._distance(left_hip, right_hip) * ratio
                waist_circumference = hip_width * 2.0
                measurements["waist_circumference"] = round(waist_circumference, 1)
                
                # 엉덩이 둘레
                hip_circumference = hip_width * 2.4
                measurements["hip_circumference"] = round(hip_circumference, 1)
            else:
                measurements["waist_circumference"] = round(170 * 0.45, 1)
                measurements["hip_circumference"] = round(170 * 0.58, 1)
            
            # 팔 길이
            left_wrist = points.get(15)
            if left_shoulder and left_wrist:
                arm_length = self._distance(left_shoulder, left_wrist) * ratio
                measurements["arm_length"] = round(arm_length, 1)
            else:
                measurements["arm_length"] = round(170 * 0.44, 1)
            
            # 다리 길이
            left_knee = points.get(25)
            left_ankle = points.get(27)
            if left_hip and left_knee and left_ankle:
                leg_length = (
                    self._distance(left_hip, left_knee) + 
                    self._distance(left_knee, left_ankle)
                ) * ratio
                measurements["leg_length"] = round(leg_length, 1)
            else:
                measurements["leg_length"] = round(170 * 0.52, 1)
            
            # 상체 길이
            nose = points.get(0)
            if nose and left_hip:
                torso_length = self._distance(nose, left_hip) * ratio
                measurements["torso_length"] = round(torso_length, 1)
            else:
                measurements["torso_length"] = round(170 * 0.48, 1)
            
            # 목 둘레 (어깨 너비 기준으로 추정)
            neck_circumference = measurements["shoulder_width"] * 0.6
            measurements["neck_circumference"] = round(neck_circumference, 1)
            
        except Exception:
            # 오류 발생 시 기본값 반환
            measurements = {
                "shoulder_width": 42.5,
                "chest_circumference": 93.5,
                "waist_circumference": 76.5,
                "hip_circumference": 98.6,
                "arm_length": 74.8,
                "leg_length": 88.4,
                "torso_length": 81.6,
                "neck_circumference": 34.0
            }
        
        return measurements
    
    def _distance(self, point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
        """두 점 사이의 거리 계산"""
        return math.sqrt(
            (point1[0] - point2[0]) ** 2 + 
            (point1[1] - point2[1]) ** 2
        )
    
    def visualize_pose(self, image_path: str, output_path: str) -> bool:
        """포즈 감지 결과를 시각화하여 저장"""
        if not MEDIAPIPE_AVAILABLE or not self.pose:
            return False
            
        try:
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            results = self.pose.process(image_rgb)
            
            if results.pose_landmarks:
                # 랜드마크 그리기
                annotated_image = image.copy()
                self.mp_drawing.draw_landmarks(
                    annotated_image,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS
                )
                
                cv2.imwrite(output_path, annotated_image)
                return True
            
            return False
        except Exception:
            return False
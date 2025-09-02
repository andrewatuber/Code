import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
import os
from datetime import datetime
import json
from config import settings
import mediapipe as mp

class VirtualFitting:
    def __init__(self):
        self.fit_tolerance = settings.FIT_TOLERANCE
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
    def generate_fitting(self, model_data: Dict[str, Any], clothing_data: Dict[str, Any]) -> str:
        """모델과 옷 데이터를 기반으로 가상 피팅 이미지를 생성합니다."""
        try:
            # 모델 이미지 로드
            model_image = cv2.imread(model_data["image_path"])
            if model_image is None:
                raise ValueError("모델 이미지를 불러올 수 없습니다.")
            
            # 옷 이미지 로드 (알파 채널 지원)
            clothing_image = cv2.imread(clothing_data["image_path"], cv2.IMREAD_UNCHANGED)
            if clothing_image is None:
                raise ValueError("옷 이미지를 불러올 수 없습니다.")
            
            # 이미지 채널 수 확인 및 정규화
            if len(clothing_image.shape) == 3 and clothing_image.shape[2] == 4:
                # 4채널 RGBA 이미지인 경우
                print(f"4채널 RGBA 이미지 감지: {clothing_image.shape}")
            elif len(clothing_image.shape) == 3 and clothing_image.shape[2] == 3:
                # 3채널 BGR 이미지인 경우
                print(f"3채널 BGR 이미지 감지: {clothing_image.shape}")
            else:
                print(f"이미지 형식: {clothing_image.shape}")
            
            # 피팅 분석
            fit_analysis = self._analyze_fit(model_data["measurements"], clothing_data["measurements"])
            
            # 포즈 감지 및 신체 부위 매핑
            pose_landmarks = self._detect_pose(model_image)
            
            # 합성 이미지 생성
            result_image = self._create_realistic_fitting(
                model_image, 
                clothing_image, 
                model_data, 
                clothing_data, 
                fit_analysis,
                pose_landmarks
            )
            
            # 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"fitting_result_{timestamp}.jpg"
            result_path = os.path.join(settings.RESULTS_DIR, result_filename)
            
            cv2.imwrite(result_path, result_image)
            
            # 피팅 정보도 함께 저장
            fit_info = {
                "model_measurements": model_data["measurements"],
                "clothing_data": clothing_data,
                "fit_analysis": fit_analysis,
                "timestamp": timestamp
            }
            
            info_path = os.path.join(settings.RESULTS_DIR, f"{result_filename}_info.json")
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(fit_info, f, ensure_ascii=False, indent=2)
            
            return result_path
            
        except Exception as e:
            print(f"가상 피팅 생성 중 오류 발생: {e}")
            raise
    
    def _analyze_fit(self, body_measurements: Dict[str, float], clothing_measurements: Dict[str, float]) -> Dict[str, Any]:
        """신체 치수와 옷 치수를 비교하여 피팅 상태를 분석합니다."""
        fit_analysis = {
            "overall_fit": "good",
            "details": {},
            "recommendations": []
        }
        
        # 주요 부위별 피팅 분석
        key_measurements = [
            ("chest_circumference", "chest", "가슴"),
            ("waist_circumference", "waist", "허리"),
            ("hip_circumference", "hip", "엉덩이"),
            ("shoulder_width", "shoulder", "어깨")
        ]
        
        tight_count = 0
        loose_count = 0
        
        for body_key, clothing_key, korean_name in key_measurements:
            if body_key in body_measurements and clothing_key in clothing_measurements:
                body_size = body_measurements[body_key]
                clothing_size = clothing_measurements[clothing_key]
                
                # 피팅 상태 계산
                fit_ratio = clothing_size / body_size
                
                if fit_ratio < 1.0:
                    status = "tight"
                    tight_count += 1
                elif fit_ratio < 1.0 + self.fit_tolerance:
                    status = "perfect"
                elif fit_ratio < 1.2:
                    status = "loose"
                    loose_count += 1
                else:
                    status = "very_loose"
                    loose_count += 1
                
                fit_analysis["details"][korean_name] = {
                    "body_size": body_size,
                    "clothing_size": clothing_size,
                    "fit_ratio": round(fit_ratio, 2),
                    "status": status
                }
        
        # 전체적인 피팅 상태 결정
        if tight_count > 2:
            fit_analysis["overall_fit"] = "too_tight"
            fit_analysis["recommendations"].append("더 큰 사이즈를 추천합니다.")
        elif loose_count > 2:
            fit_analysis["overall_fit"] = "too_loose"
            fit_analysis["recommendations"].append("더 작은 사이즈를 추천합니다.")
        elif tight_count > 0:
            fit_analysis["overall_fit"] = "slightly_tight"
            fit_analysis["recommendations"].append("일부 부위가 타이트할 수 있습니다.")
        elif loose_count > 0:
            fit_analysis["overall_fit"] = "slightly_loose"
            fit_analysis["recommendations"].append("여유 있는 핏입니다.")
        else:
            fit_analysis["recommendations"].append("완벽한 핏입니다!")
        
        return fit_analysis
    
    def _detect_pose(self, image: np.ndarray) -> Optional[Any]:
        """MediaPipe를 사용하여 포즈를 감지합니다."""
        with self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=True,
            min_detection_confidence=0.5
        ) as pose:
            results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            return results
    
    def _create_realistic_fitting(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any],
        pose_landmarks: Any
    ) -> np.ndarray:
        """현실적인 가상 피팅 이미지를 생성합니다."""
        
        # 모델 이미지 복사
        result = model_image.copy()
        model_h, model_w = result.shape[:2]
        
        # 옷 이미지 전처리 (배경 제거)
        processed_clothing = self._remove_background(clothing_image)
        
        # 포즈 기반 신체 부위 매핑
        if pose_landmarks and pose_landmarks.pose_landmarks:
            # 상의인 경우
            if self._is_upper_clothing(clothing_data):
                result = self._fit_upper_clothing(
                    result, processed_clothing, pose_landmarks, 
                    model_data, clothing_data, fit_analysis
                )
            # 하의인 경우
            elif self._is_lower_clothing(clothing_data):
                result = self._fit_lower_clothing(
                    result, processed_clothing, pose_landmarks,
                    model_data, clothing_data, fit_analysis
                )
            # 원피스인 경우
            else:
                result = self._fit_dress(
                    result, processed_clothing, pose_landmarks,
                    model_data, clothing_data, fit_analysis
                )
        
        # 피팅 정보 오버레이
        result = self._add_enhanced_fit_info_overlay(result, fit_analysis)
        
        return result
    
    def _remove_background(self, image: np.ndarray) -> np.ndarray:
        """옷 이미지에서 배경을 제거합니다."""
        try:
            # 이미지 채널 수 확인
            if len(image.shape) == 3 and image.shape[2] == 4:
                # 4채널 RGBA 이미지인 경우
                # RGB 채널만 추출하여 BGR로 변환
                rgb_image = image[:, :, :3]
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                # 3채널 BGR 이미지인 경우
                bgr_image = image.copy()
            else:
                # 그레이스케일이거나 다른 형식인 경우
                print(f"지원하지 않는 이미지 형식: shape={image.shape}")
                return image
            
            # HSV 색공간으로 변환
            hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
            
            # 흰색 배경 제거 (HSV에서 흰색은 높은 밝기, 낮은 채도)
            lower_white = np.array([0, 0, 200])
            upper_white = np.array([180, 30, 255])
            
            # 마스크 생성
            mask = cv2.inRange(hsv, lower_white, upper_white)
            mask = cv2.bitwise_not(mask)
            
            # 노이즈 제거
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # 마스크 적용
            if len(image.shape) == 3 and image.shape[2] == 4:
                # 4채널 이미지인 경우 알파 채널도 처리
                result = image.copy()
                result[mask == 0, 3] = 0  # 알파 채널을 0으로 설정
            else:
                # 3채널 이미지인 경우
                result = bgr_image.copy()
                result[mask == 0] = [0, 0, 0]
            
            return result
            
        except Exception as e:
            print(f"배경 제거 중 오류 발생: {e}")
            return image
    
    def _is_upper_clothing(self, clothing_data: Dict[str, Any]) -> bool:
        """상의인지 판단합니다."""
        clothing_type = clothing_data.get("type", "").lower()
        return any(keyword in clothing_type for keyword in ["shirt", "t-shirt", "blouse", "sweater", "jacket", "상의", "티셔츠", "블라우스"])
    
    def _is_lower_clothing(self, clothing_data: Dict[str, Any]) -> bool:
        """하의인지 판단합니다."""
        clothing_type = clothing_data.get("type", "").lower()
        return any(keyword in clothing_type for keyword in ["pants", "jeans", "skirt", "shorts", "하의", "바지", "치마"])
    
    def _fit_upper_clothing(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_landmarks: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any]
    ) -> np.ndarray:
        """상의를 모델에 피팅합니다."""
        result = model_image.copy()
        
        if not pose_landmarks.pose_landmarks:
            return result
        
        landmarks = pose_landmarks.pose_landmarks.landmark
        
        # 어깨와 가슴 위치 추출
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        
        # 이미지 좌표로 변환
        h, w = result.shape[:2]
        left_shoulder_x, left_shoulder_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        right_shoulder_x, right_shoulder_y = int(right_shoulder.x * w), int(right_shoulder.y * h)
        left_hip_x, left_hip_y = int(left_hip.x * w), int(left_hip.y * h)
        
        # 어깨 너비 계산
        shoulder_width = abs(right_shoulder_x - left_shoulder_x)
        torso_height = abs(left_hip_y - left_shoulder_y)
        
        # 옷 이미지 크기 조정
        clothing_h, clothing_w = clothing_image.shape[:2]
        scale_x = shoulder_width / clothing_w * 1.2  # 약간 여유있게
        scale_y = torso_height / clothing_h * 0.8   # 상체 길이에 맞게
        
        new_w = int(clothing_w * scale_x)
        new_h = int(clothing_h * scale_y)
        
        scaled_clothing = cv2.resize(clothing_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # 옷을 어깨 위치에 배치
        start_x = left_shoulder_x - new_w // 2
        start_y = left_shoulder_y - new_h // 4
        
        # 블렌딩
        result = self._blend_clothing_on_model(result, scaled_clothing, start_x, start_y, fit_analysis)
        
        return result
    
    def _fit_lower_clothing(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_landmarks: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any]
    ) -> np.ndarray:
        """하의를 모델에 피팅합니다."""
        result = model_image.copy()
        
        if not pose_landmarks.pose_landmarks:
            return result
        
        landmarks = pose_landmarks.pose_landmarks.landmark
        
        # 엉덩이와 무릎 위치 추출
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
        
        # 이미지 좌표로 변환
        h, w = result.shape[:2]
        left_hip_x, left_hip_y = int(left_hip.x * w), int(left_hip.y * h)
        left_knee_x, left_knee_y = int(left_knee.x * w), int(left_knee.y * h)
        
        # 하체 치수 계산
        hip_width = abs(left_hip_x - (w - left_hip_x))  # 대략적인 엉덩이 너비
        leg_height = abs(left_knee_y - left_hip_y)
        
        # 옷 이미지 크기 조정
        clothing_h, clothing_w = clothing_image.shape[:2]
        scale_x = hip_width / clothing_w * 1.1
        scale_y = leg_height / clothing_h * 1.5
        
        new_w = int(clothing_w * scale_x)
        new_h = int(clothing_h * scale_y)
        
        scaled_clothing = cv2.resize(clothing_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # 옷을 엉덩이 위치에 배치
        start_x = left_hip_x - new_w // 2
        start_y = left_hip_y - new_h // 4
        
        # 블렌딩
        result = self._blend_clothing_on_model(result, scaled_clothing, start_x, start_y, fit_analysis)
        
        return result
    
    def _fit_dress(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_landmarks: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any]
    ) -> np.ndarray:
        """원피스를 모델에 피팅합니다."""
        result = model_image.copy()
        
        if not pose_landmarks.pose_landmarks:
            return result
        
        landmarks = pose_landmarks.pose_landmarks.landmark
        
        # 어깨와 엉덩이 위치 추출
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        
        # 이미지 좌표로 변환
        h, w = result.shape[:2]
        left_shoulder_x, left_shoulder_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        left_hip_x, left_hip_y = int(left_hip.x * w), int(left_hip.y * h)
        
        # 전체 치수 계산
        shoulder_width = abs(left_shoulder_x - (w - left_shoulder_x))
        dress_height = abs(left_hip_y - left_shoulder_y) * 1.8  # 원피스는 더 길게
        
        # 옷 이미지 크기 조정
        clothing_h, clothing_w = clothing_image.shape[:2]
        scale_x = shoulder_width / clothing_w * 1.1
        scale_y = dress_height / clothing_h
        
        new_w = int(clothing_w * scale_x)
        new_h = int(clothing_h * scale_y)
        
        scaled_clothing = cv2.resize(clothing_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # 옷을 어깨 위치에 배치
        start_x = left_shoulder_x - new_w // 2
        start_y = left_shoulder_y - new_h // 4
        
        # 블렌딩
        result = self._blend_clothing_on_model(result, scaled_clothing, start_x, start_y, fit_analysis)
        
        return result
    
    def _blend_clothing_on_model(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        start_x: int, 
        start_y: int,
        fit_analysis: Dict[str, Any]
    ) -> np.ndarray:
        """옷을 모델 이미지에 자연스럽게 블렌딩합니다."""
        try:
            result = model_image.copy()
            h, w = result.shape[:2]
            clothing_h, clothing_w = clothing_image.shape[:2]
            
            # 범위 확인 및 조정
            start_x = max(0, start_x)
            start_y = max(0, start_y)
            end_x = min(w, start_x + clothing_w)
            end_y = min(h, start_y + clothing_h)
            
            if end_x <= start_x or end_y <= start_y:
                return result
            
            # 실제 배치될 영역 크기
            actual_w = end_x - start_x
            actual_h = end_y - start_y
            
            # 옷 이미지도 같은 크기로 조정
            clothing_region = clothing_image[:actual_h, :actual_w]
            
            # 모델 이미지의 해당 영역 추출
            model_region = result[start_y:end_y, start_x:end_x]
            
            # 이미지 채널 수 확인 및 안전한 처리
            if len(clothing_region.shape) == 3 and clothing_region.shape[2] == 4:
                # 알파 채널이 있는 경우 (PNG 등)
                try:
                    # 알파 채널을 3채널로 확장
                    alpha = clothing_region[:, :, 3].astype(np.float32) / 255.0
                    alpha_3ch = np.stack([alpha, alpha, alpha], axis=-1)
                    
                    # RGB 채널만 추출하고 BGR로 변환 (OpenCV는 BGR 사용)
                    clothing_rgb = clothing_region[:, :, :3]
                    clothing_bgr = cv2.cvtColor(clothing_rgb, cv2.COLOR_RGB2BGR)
                    
                    # 블렌딩
                    blended_region = (clothing_bgr * alpha_3ch + model_region * (1 - alpha_3ch)).astype(np.uint8)
                    result[start_y:end_y, start_x:end_x] = blended_region
                except Exception as e:
                    print(f"4채널 이미지 처리 중 오류: {e}")
                    return result
                    
            elif len(clothing_region.shape) == 3 and clothing_region.shape[2] == 3:
                # 3채널 BGR 이미지
                try:
                    # 그레이스케일로 마스크 생성
                    gray_clothing = cv2.cvtColor(clothing_region, cv2.COLOR_BGR2GRAY)
                    _, mask = cv2.threshold(gray_clothing, 10, 255, cv2.THRESH_BINARY)
                    mask = mask.astype(np.float32) / 255.0
                    
                    # 3채널로 확장
                    mask_3ch = np.stack([mask, mask, mask], axis=-1)
                    
                    # 블렌딩
                    blended_region = (clothing_region * mask_3ch + model_region * (1 - mask_3ch)).astype(np.uint8)
                    result[start_y:end_y, start_x:end_x] = blended_region
                except Exception as e:
                    print(f"3채널 이미지 처리 중 오류: {e}")
                    return result
                    
            elif len(clothing_region.shape) == 2:
                # 그레이스케일 이미지
                try:
                    # 3채널로 확장
                    clothing_3ch = np.stack([clothing_region, clothing_region, clothing_region], axis=-1)
                    
                    # 마스크 생성
                    _, mask = cv2.threshold(clothing_region, 10, 255, cv2.THRESH_BINARY)
                    mask = mask.astype(np.float32) / 255.0
                    mask_3ch = np.stack([mask, mask, mask], axis=-1)
                    
                    # 블렌딩
                    blended_region = (clothing_3ch * mask_3ch + model_region * (1 - mask_3ch)).astype(np.uint8)
                    result[start_y:end_y, start_x:end_x] = blended_region
                except Exception as e:
                    print(f"그레이스케일 이미지 처리 중 오류: {e}")
                    return result
            else:
                # 처리할 수 없는 이미지 형식
                print(f"지원하지 않는 이미지 형식: shape={clothing_region.shape}")
                return result
                
        except Exception as e:
            print(f"이미지 블렌딩 중 오류 발생: {e}")
            return model_image
        
        return result
    
    def _add_enhanced_fit_info_overlay(self, image: np.ndarray, fit_analysis: Dict[str, Any]) -> np.ndarray:
        """피팅 정보를 이미지에 오버레이합니다."""
        result = image.copy()
        h, w = result.shape[:2]
        
        # 반투명 배경 생성
        overlay = result.copy()
        
        # 피팅 상태에 따른 색상
        fit_colors = {
            "good": (0, 255, 0),      # 초록
            "perfect": (0, 255, 0),   # 초록
            "slightly_tight": (0, 165, 255),  # 주황
            "slightly_loose": (255, 255, 0),  # 노랑
            "too_tight": (0, 0, 255),         # 빨강
            "too_loose": (255, 0, 255)        # 마젠타
        }
        
        overall_fit = fit_analysis["overall_fit"]
        color = fit_colors.get(overall_fit, (128, 128, 128))
        
        # 상단에 전체 피팅 상태 표시
        cv2.rectangle(overlay, (10, 10), (w - 10, 80), color, -1)
        cv2.addWeighted(overlay, 0.3, result, 0.7, 0, result)
        
        # 텍스트 추가
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(result, f"Overall Fit: {overall_fit.replace('_', ' ').title()}", 
                   (20, 40), font, 0.8, (255, 255, 255), 2)
        
        # 추천사항 표시
        if fit_analysis["recommendations"]:
            recommendation = fit_analysis["recommendations"][0]
            cv2.putText(result, recommendation[:50], (20, 65), font, 0.6, (255, 255, 255), 1)
        
        # 우측에 상세 정보 표시
        y_offset = 100
        for part_name, details in fit_analysis["details"].items():
            status = details["status"]
            color = fit_colors.get(status, (128, 128, 128))
            
            text = f"{part_name}: {status}"
            cv2.putText(result, text, (w - 200, y_offset), font, 0.5, color, 1)
            y_offset += 25
        
        return result
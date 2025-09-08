import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
import os
from datetime import datetime
import json
from config import settings
import mediapipe as mp
from scipy import ndimage
from sklearn.cluster import KMeans

class AdvancedVirtualFitting:
    """향상된 가상 피팅 시스템 - 더 현실적인 결과를 위한 고급 기능 포함"""
    
    def __init__(self):
        self.fit_tolerance = settings.FIT_TOLERANCE
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        
    def generate_fitting(self, model_data: Dict[str, Any], clothing_data: Dict[str, Any]) -> str:
        """향상된 가상 피팅 이미지를 생성합니다."""
        try:
            # 모델 이미지 로드
            model_image = cv2.imread(model_data["image_path"])
            if model_image is None:
                raise ValueError("모델 이미지를 불러올 수 없습니다.")
            
            # 옷 이미지 로드 (알파 채널 지원)
            clothing_image = cv2.imread(clothing_data["image_path"], cv2.IMREAD_UNCHANGED)
            if clothing_image is None:
                raise ValueError("옷 이미지를 불러올 수 없습니다.")
            
            print(f"모델 이미지 크기: {model_image.shape}")
            print(f"옷 이미지 크기: {clothing_image.shape}")
            
            # 피팅 분석
            fit_analysis = self._analyze_fit(model_data["measurements"], clothing_data["measurements"])
            
            # 포즈 감지 및 신체 부위 매핑
            pose_results = self._detect_pose(model_image)
            
            # 신체 세그멘테이션
            body_mask = self._segment_body(model_image)
            
            # 향상된 합성 이미지 생성
            result_image = self._create_advanced_fitting(
                model_image, 
                clothing_image, 
                model_data, 
                clothing_data, 
                fit_analysis,
                pose_results,
                body_mask
            )
            
            # 후처리 - 조명 및 색상 매칭
            result_image = self._post_process(result_image, model_image)
            
            # 결과 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"advanced_fitting_result_{timestamp}.jpg"
            result_path = os.path.join(settings.RESULTS_DIR, result_filename)
            
            cv2.imwrite(result_path, result_image)
            
            # 피팅 정보도 함께 저장
            fit_info = {
                "model_measurements": model_data["measurements"],
                "clothing_data": clothing_data,
                "fit_analysis": fit_analysis,
                "timestamp": timestamp,
                "advanced_features": {
                    "body_segmentation": True,
                    "3d_warping": True,
                    "lighting_matching": True,
                    "texture_preservation": True
                }
            }
            
            info_path = os.path.join(settings.RESULTS_DIR, f"{result_filename}_info.json")
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(fit_info, f, ensure_ascii=False, indent=2)
            
            return result_path
            
        except Exception as e:
            print(f"향상된 가상 피팅 생성 중 오류 발생: {e}")
            raise
    
    def _segment_body(self, image: np.ndarray) -> np.ndarray:
        """MediaPipe를 사용한 신체 세그멘테이션"""
        with self.mp_selfie_segmentation.SelfieSegmentation(model_selection=1) as selfie_segmentation:
            # RGB로 변환
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = selfie_segmentation.process(image_rgb)
            
            # 마스크 생성
            condition = np.stack((results.segmentation_mask,) * 3, axis=-1) > 0.1
            mask = np.where(condition, 255, 0).astype(np.uint8)
            
            # 마스크 개선 - 모폴로지 연산
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask[:,:,0], cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # 가우시안 블러로 부드럽게
            mask = cv2.GaussianBlur(mask, (5, 5), 0)
            
            return mask
    
    def _analyze_fit(self, body_measurements: Dict[str, float], clothing_measurements: Dict[str, float]) -> Dict[str, Any]:
        """향상된 피팅 분석"""
        fit_analysis = {
            "overall_fit": "good",
            "details": {},
            "recommendations": [],
            "fit_score": 0.0,
            "adjustments_needed": {}
        }
        
        # 주요 부위별 피팅 분석
        key_measurements = [
            ("chest_circumference", "chest", "가슴", 1.0),
            ("waist_circumference", "waist", "허리", 0.9),
            ("hip_circumference", "hip", "엉덩이", 0.8),
            ("shoulder_width", "shoulder", "어깨", 1.1)
        ]
        
        total_score = 0
        measurement_count = 0
        
        for body_key, clothing_key, korean_name, weight in key_measurements:
            if body_key in body_measurements and clothing_key in clothing_measurements:
                body_size = body_measurements[body_key]
                clothing_size = clothing_measurements[clothing_key]
                
                # 피팅 비율 계산
                fit_ratio = clothing_size / body_size
                
                # 점수 계산 (1.0에 가까울수록 높은 점수)
                deviation = abs(1.0 - fit_ratio)
                score = max(0, 1.0 - deviation) * weight
                total_score += score
                measurement_count += 1
                
                # 상태 판정
                if fit_ratio < 0.95:
                    status = "too_tight"
                    adjustment = "increase"
                elif fit_ratio < 1.0:
                    status = "tight"
                    adjustment = "slight_increase"
                elif fit_ratio < 1.0 + self.fit_tolerance:
                    status = "perfect"
                    adjustment = "none"
                elif fit_ratio < 1.2:
                    status = "loose"
                    adjustment = "slight_decrease"
                else:
                    status = "very_loose"
                    adjustment = "decrease"
                
                fit_analysis["details"][korean_name] = {
                    "body_size": body_size,
                    "clothing_size": clothing_size,
                    "fit_ratio": round(fit_ratio, 2),
                    "status": status,
                    "score": round(score, 2)
                }
                
                if adjustment != "none":
                    fit_analysis["adjustments_needed"][korean_name] = {
                        "type": adjustment,
                        "amount": round(abs(clothing_size - body_size), 1)
                    }
        
        # 전체 피팅 점수 계산
        if measurement_count > 0:
            fit_analysis["fit_score"] = round(total_score / measurement_count * 100, 1)
        
        # 전체적인 피팅 상태 결정
        if fit_analysis["fit_score"] >= 85:
            fit_analysis["overall_fit"] = "excellent"
            fit_analysis["recommendations"].append("완벽한 핏입니다!")
        elif fit_analysis["fit_score"] >= 70:
            fit_analysis["overall_fit"] = "good"
            fit_analysis["recommendations"].append("좋은 핏입니다. 약간의 조정이 필요할 수 있습니다.")
        elif fit_analysis["fit_score"] >= 50:
            fit_analysis["overall_fit"] = "moderate"
            fit_analysis["recommendations"].append("착용 가능하지만 사이즈 조정을 권장합니다.")
        else:
            fit_analysis["overall_fit"] = "poor"
            fit_analysis["recommendations"].append("사이즈가 맞지 않습니다. 다른 사이즈를 선택해주세요.")
        
        return fit_analysis
    
    def _detect_pose(self, image: np.ndarray) -> Optional[Any]:
        """향상된 포즈 감지"""
        with self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=True,
            min_detection_confidence=0.5
        ) as pose:
            results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            return results
    
    def _create_advanced_fitting(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any],
        pose_results: Any,
        body_mask: np.ndarray
    ) -> np.ndarray:
        """향상된 가상 피팅 이미지 생성"""
        
        # 모델 이미지 복사
        result = model_image.copy()
        model_h, model_w = result.shape[:2]
        
        # 옷 이미지 전처리
        processed_clothing = self._advanced_remove_background(clothing_image)
        
        # 색상 매칭
        processed_clothing = self._match_colors(processed_clothing, model_image)
        
        # 포즈 기반 신체 부위 매핑
        if pose_results and pose_results.pose_landmarks:
            # 상의인 경우
            if self._is_upper_clothing(clothing_data):
                result = self._fit_upper_clothing_advanced(
                    result, processed_clothing, pose_results, 
                    model_data, clothing_data, fit_analysis, body_mask
                )
            # 하의인 경우
            elif self._is_lower_clothing(clothing_data):
                result = self._fit_lower_clothing_advanced(
                    result, processed_clothing, pose_results,
                    model_data, clothing_data, fit_analysis, body_mask
                )
            # 원피스인 경우
            else:
                result = self._fit_dress_advanced(
                    result, processed_clothing, pose_results,
                    model_data, clothing_data, fit_analysis, body_mask
                )
        
        # 향상된 피팅 정보 오버레이
        result = self._add_professional_overlay(result, fit_analysis)
        
        return result
    
    def _advanced_remove_background(self, image: np.ndarray) -> np.ndarray:
        """향상된 배경 제거 알고리즘"""
        try:
            if len(image.shape) == 3 and image.shape[2] == 4:
                # RGBA 이미지 - 알파 채널 활용
                alpha = image[:, :, 3]
                
                # 알파 채널 개선
                _, alpha = cv2.threshold(alpha, 50, 255, cv2.THRESH_BINARY)
                
                # 모폴로지 연산으로 노이즈 제거
                kernel = np.ones((3, 3), np.uint8)
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
                
                # 엣지 부드럽게
                alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
                
                # 결과 이미지 생성
                result = image.copy()
                result[:, :, 3] = alpha
                return result
                
            else:
                # BGR 이미지 - GrabCut 알고리즘 사용
                bgr_image = image.copy() if len(image.shape) == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                
                # GrabCut을 위한 초기 마스크 생성
                mask = np.zeros(bgr_image.shape[:2], np.uint8)
                
                # 초기 사각형 설정 (이미지 중앙 80% 영역)
                h, w = bgr_image.shape[:2]
                rect = (int(w * 0.1), int(h * 0.1), int(w * 0.8), int(h * 0.8))
                
                # GrabCut 알고리즘 적용
                bgModel = np.zeros((1, 65), np.float64)
                fgModel = np.zeros((1, 65), np.float64)
                
                try:
                    cv2.grabCut(bgr_image, mask, rect, bgModel, fgModel, 5, cv2.GC_INIT_WITH_RECT)
                    
                    # 마스크 처리
                    mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype('uint8')
                    
                    # 모폴로지 연산
                    kernel = np.ones((5, 5), np.uint8)
                    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel)
                    mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
                    
                    # 부드럽게 처리
                    mask2 = cv2.GaussianBlur(mask2, (5, 5), 0)
                    
                    # 4채널 이미지 생성
                    result = np.zeros((h, w, 4), dtype=np.uint8)
                    result[:, :, :3] = bgr_image
                    result[:, :, 3] = mask2
                    
                    return result
                    
                except:
                    # GrabCut 실패 시 기본 방법 사용
                    return self._simple_background_removal(bgr_image)
                    
        except Exception as e:
            print(f"향상된 배경 제거 중 오류: {e}")
            return image
    
    def _simple_background_removal(self, image: np.ndarray) -> np.ndarray:
        """간단한 배경 제거 (폴백)"""
        # HSV 색공간으로 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 흰색 배경 제거
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        
        mask = cv2.inRange(hsv, lower_white, upper_white)
        mask = cv2.bitwise_not(mask)
        
        # 4채널 이미지 생성
        h, w = image.shape[:2]
        result = np.zeros((h, w, 4), dtype=np.uint8)
        result[:, :, :3] = image
        result[:, :, 3] = mask
        
        return result
    
    def _match_colors(self, clothing: np.ndarray, model_image: np.ndarray) -> np.ndarray:
        """옷의 색상을 모델 이미지의 조명에 맞게 조정"""
        try:
            # 모델 이미지의 평균 밝기와 색조 계산
            model_lab = cv2.cvtColor(model_image, cv2.COLOR_BGR2LAB)
            model_l_mean = np.mean(model_lab[:, :, 0])
            
            # 옷 이미지의 색상 조정
            if len(clothing.shape) == 3 and clothing.shape[2] >= 3:
                clothing_bgr = clothing[:, :, :3]
                clothing_lab = cv2.cvtColor(clothing_bgr, cv2.COLOR_BGR2LAB)
                
                # 밝기 조정
                clothing_l_mean = np.mean(clothing_lab[:, :, 0])
                brightness_ratio = model_l_mean / clothing_l_mean if clothing_l_mean > 0 else 1.0
                
                # 부드러운 조정 (극단적인 변화 방지)
                brightness_ratio = np.clip(brightness_ratio, 0.7, 1.3)
                
                clothing_lab[:, :, 0] = np.clip(clothing_lab[:, :, 0] * brightness_ratio, 0, 255)
                
                # BGR로 다시 변환
                adjusted_bgr = cv2.cvtColor(clothing_lab, cv2.COLOR_LAB2BGR)
                
                # 결과 이미지 생성
                result = clothing.copy()
                result[:, :, :3] = adjusted_bgr
                
                return result
            
            return clothing
            
        except Exception as e:
            print(f"색상 매칭 중 오류: {e}")
            return clothing
    
    def _fit_upper_clothing_advanced(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_results: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any],
        body_mask: np.ndarray
    ) -> np.ndarray:
        """향상된 상의 피팅"""
        result = model_image.copy()
        
        if not pose_results.pose_landmarks:
            return result
        
        landmarks = pose_results.pose_landmarks.landmark
        h, w = result.shape[:2]
        
        # 주요 포인트 추출
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        left_elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        
        # 좌표 변환
        points = {
            'left_shoulder': (int(left_shoulder.x * w), int(left_shoulder.y * h)),
            'right_shoulder': (int(right_shoulder.x * w), int(right_shoulder.y * h)),
            'left_hip': (int(left_hip.x * w), int(left_hip.y * h)),
            'right_hip': (int(right_hip.x * w), int(right_hip.y * h)),
            'left_elbow': (int(left_elbow.x * w), int(left_elbow.y * h)),
            'right_elbow': (int(right_elbow.x * w), int(right_elbow.y * h))
        }
        
        # 3D 변환을 위한 원근 변환 계산
        src_points = np.float32([
            [0, 0],
            [clothing_image.shape[1], 0],
            [clothing_image.shape[1], clothing_image.shape[0]],
            [0, clothing_image.shape[0]]
        ])
        
        # 목표 지점 계산 (신체 형태에 맞게)
        shoulder_width = abs(points['right_shoulder'][0] - points['left_shoulder'][0])
        torso_height = abs(points['left_hip'][1] - points['left_shoulder'][1])
        
        # 피팅 분석 결과를 반영한 크기 조정
        fit_ratio = 1.0
        if 'details' in fit_analysis and '가슴' in fit_analysis['details']:
            fit_ratio = fit_analysis['details']['가슴']['fit_ratio']
        
        # 크기 조정 (피팅 비율 반영)
        adjusted_width = int(shoulder_width * 1.2 * min(fit_ratio, 1.2))
        adjusted_height = int(torso_height * 1.1)
        
        # 목표 사각형
        center_x = (points['left_shoulder'][0] + points['right_shoulder'][0]) // 2
        center_y = (points['left_shoulder'][1] + points['left_hip'][1]) // 2
        
        dst_points = np.float32([
            [center_x - adjusted_width // 2, center_y - adjusted_height // 2],
            [center_x + adjusted_width // 2, center_y - adjusted_height // 2],
            [center_x + adjusted_width // 2, center_y + adjusted_height // 2],
            [center_x - adjusted_width // 2, center_y + adjusted_height // 2]
        ])
        
        # 원근 변환 매트릭스
        M = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # 옷 이미지 변환
        warped_clothing = cv2.warpPerspective(clothing_image, M, (w, h))
        
        # 신체 곡선에 맞게 추가 변형 (메시 워핑)
        warped_clothing = self._apply_body_curve_warping(warped_clothing, points, 'upper')
        
        # 고급 블렌딩
        result = self._advanced_blend(result, warped_clothing, body_mask, fit_analysis)
        
        return result
    
    def _fit_lower_clothing_advanced(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_results: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any],
        body_mask: np.ndarray
    ) -> np.ndarray:
        """향상된 하의 피팅"""
        result = model_image.copy()
        
        if not pose_results.pose_landmarks:
            return result
        
        landmarks = pose_results.pose_landmarks.landmark
        h, w = result.shape[:2]
        
        # 주요 포인트 추출
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
        right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        
        # 좌표 변환
        points = {
            'left_hip': (int(left_hip.x * w), int(left_hip.y * h)),
            'right_hip': (int(right_hip.x * w), int(right_hip.y * h)),
            'left_knee': (int(left_knee.x * w), int(left_knee.y * h)),
            'right_knee': (int(right_knee.x * w), int(right_knee.y * h)),
            'left_ankle': (int(left_ankle.x * w), int(left_ankle.y * h)),
            'right_ankle': (int(right_ankle.x * w), int(right_ankle.y * h))
        }
        
        # 하의 크기 계산
        hip_width = abs(points['right_hip'][0] - points['left_hip'][0])
        leg_height = abs(points['left_ankle'][1] - points['left_hip'][1])
        
        # 피팅 분석 결과 반영
        fit_ratio = 1.0
        if 'details' in fit_analysis and '엉덩이' in fit_analysis['details']:
            fit_ratio = fit_analysis['details']['엉덩이']['fit_ratio']
        
        # 크기 조정
        adjusted_width = int(hip_width * 2.0 * min(fit_ratio, 1.2))
        adjusted_height = int(leg_height * 1.1)
        
        # 원근 변환 적용
        src_points = np.float32([
            [0, 0],
            [clothing_image.shape[1], 0],
            [clothing_image.shape[1], clothing_image.shape[0]],
            [0, clothing_image.shape[0]]
        ])
        
        center_x = (points['left_hip'][0] + points['right_hip'][0]) // 2
        
        dst_points = np.float32([
            [center_x - adjusted_width // 2, points['left_hip'][1]],
            [center_x + adjusted_width // 2, points['right_hip'][1]],
            [center_x + adjusted_width // 2, points['left_ankle'][1]],
            [center_x - adjusted_width // 2, points['right_ankle'][1]]
        ])
        
        M = cv2.getPerspectiveTransform(src_points, dst_points)
        warped_clothing = cv2.warpPerspective(clothing_image, M, (w, h))
        
        # 다리 곡선에 맞게 변형
        warped_clothing = self._apply_body_curve_warping(warped_clothing, points, 'lower')
        
        # 고급 블렌딩
        result = self._advanced_blend(result, warped_clothing, body_mask, fit_analysis)
        
        return result
    
    def _fit_dress_advanced(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        pose_results: Any,
        model_data: Dict[str, Any],
        clothing_data: Dict[str, Any],
        fit_analysis: Dict[str, Any],
        body_mask: np.ndarray
    ) -> np.ndarray:
        """향상된 원피스 피팅"""
        result = model_image.copy()
        
        if not pose_results.pose_landmarks:
            return result
        
        landmarks = pose_results.pose_landmarks.landmark
        h, w = result.shape[:2]
        
        # 전신 포인트 추출
        points = {}
        key_landmarks = [
            ('left_shoulder', self.mp_pose.PoseLandmark.LEFT_SHOULDER),
            ('right_shoulder', self.mp_pose.PoseLandmark.RIGHT_SHOULDER),
            ('left_hip', self.mp_pose.PoseLandmark.LEFT_HIP),
            ('right_hip', self.mp_pose.PoseLandmark.RIGHT_HIP),
            ('left_knee', self.mp_pose.PoseLandmark.LEFT_KNEE),
            ('right_knee', self.mp_pose.PoseLandmark.RIGHT_KNEE)
        ]
        
        for name, landmark_id in key_landmarks:
            landmark = landmarks[landmark_id]
            points[name] = (int(landmark.x * w), int(landmark.y * h))
        
        # 원피스 크기 계산
        shoulder_width = abs(points['right_shoulder'][0] - points['left_shoulder'][0])
        dress_height = abs(points['left_knee'][1] - points['left_shoulder'][1]) * 1.2
        
        # 피팅 분석 결과 반영
        fit_ratio = 1.0
        if 'details' in fit_analysis:
            # 가슴과 허리의 평균 비율 사용
            chest_ratio = fit_analysis['details'].get('가슴', {}).get('fit_ratio', 1.0)
            waist_ratio = fit_analysis['details'].get('허리', {}).get('fit_ratio', 1.0)
            fit_ratio = (chest_ratio + waist_ratio) / 2
        
        # 크기 조정
        adjusted_width = int(shoulder_width * 1.3 * min(fit_ratio, 1.2))
        adjusted_height = int(dress_height)
        
        # 원근 변환
        src_points = np.float32([
            [0, 0],
            [clothing_image.shape[1], 0],
            [clothing_image.shape[1], clothing_image.shape[0]],
            [0, clothing_image.shape[0]]
        ])
        
        center_x = (points['left_shoulder'][0] + points['right_shoulder'][0]) // 2
        
        dst_points = np.float32([
            [center_x - adjusted_width // 2, points['left_shoulder'][1]],
            [center_x + adjusted_width // 2, points['right_shoulder'][1]],
            [center_x + adjusted_width // 2 + 10, points['left_shoulder'][1] + adjusted_height],
            [center_x - adjusted_width // 2 - 10, points['left_shoulder'][1] + adjusted_height]
        ])
        
        M = cv2.getPerspectiveTransform(src_points, dst_points)
        warped_clothing = cv2.warpPerspective(clothing_image, M, (w, h))
        
        # 신체 곡선에 맞게 변형
        warped_clothing = self._apply_body_curve_warping(warped_clothing, points, 'dress')
        
        # 고급 블렌딩
        result = self._advanced_blend(result, warped_clothing, body_mask, fit_analysis)
        
        return result
    
    def _apply_body_curve_warping(self, clothing: np.ndarray, body_points: Dict, clothing_type: str) -> np.ndarray:
        """신체 곡선에 맞게 옷을 변형"""
        try:
            h, w = clothing.shape[:2]
            
            # 메시 그리드 생성 - 실제 이미지 크기에 맞게
            map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32), 
                                       np.arange(h, dtype=np.float32))
            
            # 신체 곡선에 따른 변형 적용
            if clothing_type == 'upper':
                # 가슴 부분 볼륨 효과
                center_y = h // 3
                for y in range(h):
                    dist_from_center = abs(y - center_y)
                    if dist_from_center < h // 4:
                        curve_factor = 1.0 + 0.03 * np.cos(dist_from_center * np.pi / (h // 4))
                        # x 좌표를 중심으로 살짝 확장
                        for x in range(w):
                            dist_from_x_center = abs(x - w // 2)
                            if dist_from_x_center < w // 3:
                                map_x[y, x] = w // 2 + (x - w // 2) * curve_factor
            
            elif clothing_type == 'lower':
                # 다리 라인 따라 변형
                for y in range(h):
                    taper_factor = 1.0 - (y / h) * 0.15  # 아래로 갈수록 좁아짐
                    for x in range(w):
                        map_x[y, x] = w // 2 + (x - w // 2) * taper_factor
            
            # 리매핑 적용
            warped = cv2.remap(clothing, map_x, map_y, cv2.INTER_LINEAR)
            
            return warped
            
        except Exception as e:
            print(f"신체 곡선 워핑 중 오류: {e}")
            return clothing
    
    def _advanced_blend(
        self, 
        model_image: np.ndarray, 
        clothing_image: np.ndarray,
        body_mask: np.ndarray,
        fit_analysis: Dict[str, Any]
    ) -> np.ndarray:
        """향상된 블렌딩 기법"""
        try:
            result = model_image.copy()
            h, w = result.shape[:2]
            
            # 옷 이미지에서 알파 채널 추출
            if len(clothing_image.shape) == 3 and clothing_image.shape[2] == 4:
                clothing_alpha = clothing_image[:, :, 3].astype(np.float32) / 255.0
                clothing_bgr = clothing_image[:, :, :3]
            else:
                # 알파 채널이 없으면 생성
                gray = cv2.cvtColor(clothing_image, cv2.COLOR_BGR2GRAY)
                _, clothing_alpha = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
                clothing_alpha = clothing_alpha.astype(np.float32) / 255.0
                clothing_bgr = clothing_image[:, :, :3] if len(clothing_image.shape) == 3 else clothing_image
            
            # 신체 마스크와 결합
            if body_mask is not None:
                body_mask_norm = body_mask.astype(np.float32) / 255.0
                if len(body_mask_norm.shape) == 2:
                    combined_alpha = clothing_alpha * body_mask_norm
                else:
                    combined_alpha = clothing_alpha * body_mask_norm[:, :, 0]
            else:
                combined_alpha = clothing_alpha
            
            # 엣지 페더링 (부드러운 경계)
            kernel_size = 5
            combined_alpha = cv2.GaussianBlur(combined_alpha, (kernel_size, kernel_size), 0)
            
            # 피팅 품질에 따른 투명도 조정
            fit_score = fit_analysis.get('fit_score', 70) / 100.0
            opacity = 0.85 + (fit_score * 0.15)  # 피팅이 좋을수록 더 불투명하게
            combined_alpha *= opacity
            
            # 3채널로 확장
            alpha_3ch = np.stack([combined_alpha, combined_alpha, combined_alpha], axis=-1)
            
            # 포아송 블렌딩 시뮬레이션 (간단한 버전)
            # 옷 영역의 그래디언트 보존
            clothing_lap = cv2.Laplacian(clothing_bgr, cv2.CV_32F)
            model_lap = cv2.Laplacian(result, cv2.CV_32F)
            
            # 그래디언트 혼합
            mixed_lap = clothing_lap * alpha_3ch + model_lap * (1 - alpha_3ch)
            
            # 기본 블렌딩
            blended = clothing_bgr * alpha_3ch + result * (1 - alpha_3ch)
            
            # 그래디언트 정보 추가 (디테일 보존)
            detail_weight = 0.1
            blended = blended + mixed_lap * detail_weight
            
            # 클리핑
            blended = np.clip(blended, 0, 255).astype(np.uint8)
            
            # 그림자 효과 추가
            shadow = self._add_clothing_shadow(blended, combined_alpha)
            
            return shadow
            
        except Exception as e:
            print(f"향상된 블렌딩 중 오류: {e}")
            return model_image
    
    def _add_clothing_shadow(self, image: np.ndarray, alpha_mask: np.ndarray) -> np.ndarray:
        """옷에 자연스러운 그림자 추가"""
        try:
            result = image.copy()
            
            # 그림자 마스크 생성 (알파 마스크를 아래로 이동)
            shadow_mask = np.zeros_like(alpha_mask)
            offset = 5
            shadow_mask[offset:, :] = alpha_mask[:-offset, :]
            
            # 그림자 영역만 추출
            shadow_mask = shadow_mask * (1 - alpha_mask)
            
            # 부드럽게 처리
            shadow_mask = cv2.GaussianBlur(shadow_mask, (15, 15), 0)
            
            # 그림자 적용 (어둡게)
            shadow_intensity = 0.3
            for c in range(3):
                result[:, :, c] = result[:, :, c] * (1 - shadow_mask * shadow_intensity)
            
            return result.astype(np.uint8)
            
        except Exception as e:
            print(f"그림자 추가 중 오류: {e}")
            return image
    
    def _post_process(self, result: np.ndarray, original: np.ndarray) -> np.ndarray:
        """후처리 - 조명, 색상, 선명도 조정"""
        try:
            # 색상 보정
            result = cv2.addWeighted(result, 0.9, original, 0.1, 0)
            
            # 선명도 향상
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(result, -1, kernel)
            result = cv2.addWeighted(result, 0.7, sharpened, 0.3, 0)
            
            # 대비 조정
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            result = cv2.merge([l, a, b])
            result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
            
            return result
            
        except Exception as e:
            print(f"후처리 중 오류: {e}")
            return result
    
    def _add_professional_overlay(self, image: np.ndarray, fit_analysis: Dict[str, Any]) -> np.ndarray:
        """전문적인 피팅 정보 오버레이"""
        result = image.copy()
        h, w = result.shape[:2]
        
        # 반투명 오버레이 생성
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 피팅 점수에 따른 색상
        fit_score = fit_analysis.get('fit_score', 0)
        if fit_score >= 85:
            base_color = (0, 255, 0)  # 초록
        elif fit_score >= 70:
            base_color = (0, 200, 255)  # 주황
        elif fit_score >= 50:
            base_color = (0, 165, 255)  # 진한 주황
        else:
            base_color = (0, 0, 255)  # 빨강
        
        # 상단 패널
        panel_height = 120
        cv2.rectangle(overlay, (0, 0), (w, panel_height), (40, 40, 40), -1)
        
        # 그래디언트 효과
        for i in range(panel_height):
            alpha = 1.0 - (i / panel_height) * 0.3
            overlay[i, :] = overlay[i, :] * alpha
        
        # 오버레이 적용
        result = cv2.addWeighted(result, 1.0, overlay, 0.7, 0)
        
        # 텍스트 스타일
        font = cv2.FONT_HERSHEY_DUPLEX
        
        # 메인 타이틀
        title = f"AI Virtual Fitting Analysis"
        cv2.putText(result, title, (20, 35), font, 0.9, (255, 255, 255), 2)
        
        # 피팅 점수 (큰 폰트)
        score_text = f"Fit Score: {fit_score:.1f}%"
        cv2.putText(result, score_text, (20, 70), font, 0.8, base_color, 2)
        
        # 전체 상태
        status = fit_analysis.get('overall_fit', 'unknown').replace('_', ' ').title()
        cv2.putText(result, f"Status: {status}", (20, 100), font, 0.6, (200, 200, 200), 1)
        
        # 우측 상세 패널
        detail_x = w - 250
        detail_y = 150
        
        # 상세 정보 배경
        cv2.rectangle(result, (detail_x - 10, detail_y - 10), 
                     (w - 10, detail_y + len(fit_analysis['details']) * 30 + 10), 
                     (20, 20, 20), -1)
        cv2.rectangle(result, (detail_x - 10, detail_y - 10), 
                     (w - 10, detail_y + len(fit_analysis['details']) * 30 + 10), 
                     base_color, 2)
        
        # 각 부위별 정보
        for part_name, details in fit_analysis['details'].items():
            status = details['status']
            score = details.get('score', 0)
            
            # 상태별 아이콘
            if status == 'perfect':
                icon = "✓"
                color = (0, 255, 0)
            elif 'tight' in status:
                icon = "↓"
                color = (0, 165, 255)
            elif 'loose' in status:
                icon = "↑"
                color = (255, 165, 0)
            else:
                icon = "•"
                color = (200, 200, 200)
            
            text = f"{part_name}: {status.replace('_', ' ')}"
            cv2.putText(result, text, (detail_x, detail_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            detail_y += 30
        
        # 추천사항
        if fit_analysis.get('recommendations'):
            rec_y = h - 50
            recommendation = fit_analysis['recommendations'][0]
            
            # 배경
            cv2.rectangle(result, (10, rec_y - 25), (w - 10, rec_y + 10), 
                         (40, 40, 40), -1)
            cv2.rectangle(result, (10, rec_y - 25), (w - 10, rec_y + 10), 
                         base_color, 1)
            
            # 텍스트
            cv2.putText(result, f"Recommendation: {recommendation}", 
                       (20, rec_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 조정 필요 표시
        if fit_analysis.get('adjustments_needed'):
            adjust_text = f"Adjustments needed in {len(fit_analysis['adjustments_needed'])} areas"
            cv2.putText(result, adjust_text, (20, h - 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
        
        return result
    
    def _is_upper_clothing(self, clothing_data: Dict[str, Any]) -> bool:
        """상의인지 판단"""
        clothing_type = clothing_data.get("type", "").lower()
        upper_keywords = ["shirt", "t-shirt", "blouse", "sweater", "jacket", "top", 
                         "상의", "티셔츠", "셔츠", "블라우스", "스웨터", "자켓"]
        return any(keyword in clothing_type for keyword in upper_keywords)
    
    def _is_lower_clothing(self, clothing_data: Dict[str, Any]) -> bool:
        """하의인지 판단"""
        clothing_type = clothing_data.get("type", "").lower()
        lower_keywords = ["pants", "jeans", "skirt", "shorts", "trousers", "bottom",
                         "하의", "바지", "청바지", "치마", "반바지"]
        return any(keyword in clothing_type for keyword in lower_keywords)

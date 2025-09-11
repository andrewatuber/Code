import cv2
import numpy as np
from typing import Dict, Optional, Any, Tuple
import json
from config import settings

class ClothingAnalysis:
    def __init__(self):
        # 설정에서 옷 종류별 기본 비율 가져오기
        self.clothing_ratios = settings.CLOTHING_RATIOS
    
    def analyze_clothing(
        self, 
        image_path: str, 
        width: Optional[float] = None, 
        length: Optional[float] = None,
        size_chart: Optional[Dict[str, Any]] = None,
        selected_size: Optional[str] = None # 추가된 파라미터
    ) -> Dict[str, float]:
        """옷 이미지를 분석하여 각 부위의 치수를 계산합니다."""
        
        # 이미지 로드 및 분석
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("이미지를 불러올 수 없습니다.")
        
        # 옷 종류 감지
        clothing_type = self._detect_clothing_type(image)
        
        # 사이즈 차트가 있으면 우선 사용
        if size_chart:
            parsed_chart_data = self._parse_size_chart(size_chart, clothing_type)
            if selected_size and selected_size in parsed_chart_data.get("available_sizes", {}):
                measurements = parsed_chart_data["available_sizes"][selected_size]
            else:
                # 선택된 사이즈가 없거나 유효하지 않으면 첫 번째 사이즈 또는 기본값 사용
                if parsed_chart_data.get("available_sizes"):
                    first_size_key = next(iter(parsed_chart_data["available_sizes"]))
                    measurements = parsed_chart_data["available_sizes"][first_size_key]
                else:
                    measurements = self._calculate_from_dimensions(
                        clothing_type, width, length
                    )
        else:
            # 입력된 치수를 기반으로 다른 치수들 계산
            measurements = self._calculate_from_dimensions(
                clothing_type, width, length
            )
        
        # 이미지 분석을 통한 보정
        image_measurements = self._analyze_image_proportions(image, clothing_type)
        measurements.update(image_measurements)
        
        return measurements
    
    def _detect_clothing_type(self, image: np.ndarray) -> str:
        """이미지에서 옷의 종류를 감지합니다."""
        # 간단한 형태 분석으로 옷 종류 추정
        height, width = image.shape[:2]
        aspect_ratio = height / width
        
        # 색상 분석
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 윤곽선 찾기
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return "shirt"  # 기본값
        
        # 가장 큰 윤곽선
        main_contour = max(contours, key=cv2.contourArea)
        
        # 윤곽선의 형태 분석
        x, y, w, h = cv2.boundingRect(main_contour)
        contour_aspect_ratio = h / w
        
        # 비율에 따른 옷 종류 분류
        if contour_aspect_ratio > 2.0:
            return "dress"
        elif contour_aspect_ratio > 1.5:
            if self._has_sleeves(main_contour):
                return "jacket"
            else:
                return "pants"
        else:
            return "shirt"
    
    def _has_sleeves(self, contour: np.ndarray) -> bool:
        """윤곽선에서 소매가 있는지 감지합니다."""
        # 윤곽선의 볼록 껍질 계산
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        contour_area = cv2.contourArea(contour)
        
        # 볼록성 비율 (소매가 있으면 더 복잡한 형태)
        solidity = contour_area / hull_area if hull_area > 0 else 0
        
        return solidity < 0.8  # 임계값
    
    def _calculate_from_dimensions(
        self, 
        clothing_type: str, 
        width: Optional[float], 
        length: Optional[float]
    ) -> Dict[str, float]:
        """입력된 치수를 기반으로 다른 치수들을 계산합니다."""
        measurements = {}
        ratios = self.clothing_ratios.get(clothing_type, self.clothing_ratios["shirt"])
        
        # 폭이 주어진 경우
        if width:
            measurements["width"] = width
            for key, ratio in ratios.items():
                if key != "length_to_width":
                    part_name = key.replace("_to_width", "")
                    measurements[part_name] = round(width * ratio, 1)
            
            # 길이가 따로 주어지지 않았으면 비율로 계산
            if not length:
                measurements["length"] = round(width * ratios["length_to_width"], 1)
        
        # 길이가 주어진 경우
        if length:
            measurements["length"] = length
            if not width:
                # 길이로부터 폭 역산
                width = length / ratios["length_to_width"]
                measurements["width"] = round(width, 1)
                
                # 다른 치수들 계산
                for key, ratio in ratios.items():
                    if key != "length_to_width":
                        part_name = key.replace("_to_width", "")
                        measurements[part_name] = round(width * ratio, 1)
        
        # 기본값 설정 (아무것도 주어지지 않은 경우)
        if not width and not length:
            measurements = {
                "width": 50.0,
                "length": 65.0,
                "chest": 50.0,
                "shoulder": 40.0
            }
        
        return measurements
    
    def _parse_size_chart(self, size_chart: Dict[str, Any], clothing_type: str) -> Dict[str, float]:
        """사이즈 차트를 파싱하여 치수 정보를 추출합니다."""
        all_sizes_measurements = {"available_sizes": {}}
        
        # 표준 키 이름으로 매핑
        key_mapping = {
            "가슴둘레": "chest", "가슴": "chest",
            "허리둘레": "waist", "허리": "waist",
            "엉덩이둘레": "hip", "엉덩이": "hip",
            "어깨너비": "shoulder", "어깨": "shoulder",
            "소매길이": "sleeve", "소매": "sleeve",
            "총길이": "length", "기장": "length",
            "총폭": "width", "단면폭": "width", "총장": "length",
            "chest_circumference": "chest",
            "waist_circumference": "waist",
            "hip_circumference": "hip",
            "shoulder_width": "shoulder",
            "sleeve_length": "sleeve",
            "total_length": "length",
            "total_width": "width"
        }
        
        # OCR 서비스에서 반환된 'sizes' 키를 기반으로 파싱
        if "sizes" in size_chart and isinstance(size_chart["sizes"], dict):
            for size_name, raw_measurements in size_chart["sizes"].items():
                current_size_measurements = {}
                for key, value in raw_measurements.items():
                    mapped_key = key_mapping.get(key.lower(), key.lower())
                    try:
                        current_size_measurements[mapped_key] = float(value)
                    except (ValueError, TypeError):
                        pass # 숫자로 변환할 수 없는 값은 무시
                all_sizes_measurements["available_sizes"][size_name] = current_size_measurements
        elif "measurements" in size_chart and isinstance(size_chart["measurements"], dict):
            # 단일 사이즈 정보인 경우 (이전 버전 호환성)
            single_size_measurements = {}
            for key, value in size_chart["measurements"].items():
                mapped_key = key_mapping.get(key.lower(), key.lower())
                try:
                    single_size_measurements[mapped_key] = float(value)
                except (ValueError, TypeError):
                    pass
            all_sizes_measurements["available_sizes"]["default"] = single_size_measurements
        
        return all_sizes_measurements # 모든 사이즈 정보를 반환하도록 변경
    
    def _analyze_image_proportions(self, image: np.ndarray, clothing_type: str) -> Dict[str, float]:
        """이미지 분석을 통해 비례 관계를 파악합니다."""
        measurements = {}
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 윤곽선 찾기
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return measurements
        
        # 가장 큰 윤곽선 (옷의 메인 형태)
        main_contour = max(contours, key=cv2.contourArea)
        
        # 바운딩 박스
        x, y, w, h = cv2.boundingRect(main_contour)
        
        # 이미지 기반 비율 계산
        measurements["image_aspect_ratio"] = h / w if w > 0 else 1.0
        measurements["image_width_pixels"] = w
        measurements["image_height_pixels"] = h
        
        # 옷 종류별 특징점 분석
        if clothing_type == "shirt":
            measurements.update(self._analyze_shirt_features(main_contour, x, y, w, h))
        elif clothing_type == "pants":
            measurements.update(self._analyze_pants_features(main_contour, x, y, w, h))
        
        return measurements
    
    def _analyze_shirt_features(self, contour: np.ndarray, x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """셔츠의 특징을 분석합니다."""
        features = {}
        
        # 어깨 라인 감지 (상단 1/4 지점에서의 폭)
        shoulder_y = y + h // 4
        shoulder_points = [point[0] for point in contour if abs(point[0][1] - shoulder_y) < 5]
        
        if len(shoulder_points) >= 2:
            shoulder_width = max([p[0] for p in shoulder_points]) - min([p[0] for p in shoulder_points])
            features["shoulder_ratio"] = shoulder_width / w if w > 0 else 0.8
        
        # 허리 라인 감지 (중간 지점에서의 폭)
        waist_y = y + h // 2
        waist_points = [point[0] for point in contour if abs(point[0][1] - waist_y) < 5]
        
        if len(waist_points) >= 2:
            waist_width = max([p[0] for p in waist_points]) - min([p[0] for p in waist_points])
            features["waist_ratio"] = waist_width / w if w > 0 else 0.9
        
        return features
    
    def _analyze_pants_features(self, contour: np.ndarray, x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """바지의 특징을 분석합니다."""
        features = {}
        
        # 허리 라인 (상단)
        waist_width = w
        features["waist_ratio"] = 1.0
        
        # 엉덩이 라인 (상단 1/3 지점)
        hip_y = y + h // 3
        hip_points = [point[0] for point in contour if abs(point[0][1] - hip_y) < 5]
        
        if len(hip_points) >= 2:
            hip_width = max([p[0] for p in hip_points]) - min([p[0] for p in hip_points])
            features["hip_ratio"] = hip_width / w if w > 0 else 1.1
        
        # 다리 부분 (하단 1/3)
        leg_y = y + 2 * h // 3
        leg_points = [point[0] for point in contour if abs(point[0][1] - leg_y) < 5]
        
        if len(leg_points) >= 2:
            leg_width = max([p[0] for p in leg_points]) - min([p[0] for p in leg_points])
            features["leg_ratio"] = leg_width / w if w > 0 else 0.6
        
        return features
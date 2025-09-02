"""
OCR 서비스 모듈
사이즈 차트 이미지에서 텍스트를 추출하고 파싱합니다.
"""

import cv2
import numpy as np
import re
from typing import Dict, Any, List, Optional
import pytesseract
import json
import os

class OCRService:
    def __init__(self):
        # Tesseract 경로 설정 (macOS의 경우)
        if os.path.exists('/opt/homebrew/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        elif os.path.exists('/usr/local/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
        
        # 사이즈 관련 키워드
        self.size_keywords = {
            'korean': ['사이즈', '치수', '길이', '가슴', '어깨', '허리', '엉덩이', '총장', '폭', '너비', '소매', '밑단', '허벅지', '기장'],
            'english': ['size', 'length', 'chest', 'shoulder', 'waist', 'hip', 'width', 'sleeve', 'hem', 'thigh', 'bust', 'inseam'],
            'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE', '44', '55', '66', '77', '88', '90', '95', '100', '105', '110']
        }
        
    def extract_text_from_image(self, image_path: str) -> str:
        """이미지에서 텍스트를 추출합니다."""
        try:
            # 이미지 읽기
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("이미지를 읽을 수 없습니다.")
            
            # 이미지 전처리
            processed_image = self._preprocess_image(image)
            
            # OCR 수행 (한국어 + 영어)
            try:
                # 한국어 우선 시도
                text = pytesseract.image_to_string(processed_image, lang='kor+eng')
            except:
                # 한국어가 실패하면 영어만 시도
                try:
                    text = pytesseract.image_to_string(processed_image, lang='eng')
                except:
                    # 기본 설정으로 시도
                    text = pytesseract.image_to_string(processed_image)
            
            return text.strip()
        except Exception as e:
            print(f"OCR 오류: {e}")
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """OCR 정확도를 높이기 위한 이미지 전처리"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 노이즈 제거
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 이진화
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 모폴로지 연산으로 노이즈 제거
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary
    
    def parse_size_chart(self, text: str) -> Dict[str, Any]:
        """OCR 결과에서 사이즈 정보를 파싱합니다."""
        size_data = {
            'raw_text': text,
            'sizes': {},
            'measurements': {},
            'size_options': [],
            'size_measurements': {}
        }
        
        if not text:
            return size_data
        
        # 숫자 패턴 찾기 (사이즈 측정값)
        number_pattern = r'\d+(?:\.\d+)?'
        numbers = re.findall(number_pattern, text)
        
        # 사이즈 라벨 찾기
        size_labels = []
        text_upper = text.upper()
        for size in self.size_keywords['sizes']:
            if size in text_upper:
                size_labels.append(size)
        
        # 사이즈 옵션들을 정렬 (XS, S, M, L, XL, XXL 순서)
        size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE']
        size_labels = sorted(size_labels, key=lambda x: size_order.index(x) if x in size_order else len(size_order))
        
        size_data['size_options'] = size_labels
        
        # 측정 항목과 값 매칭
        measurements = self._extract_measurements(text)
        size_data['measurements'] = measurements
        
        # 사이즈별 데이터 구조화
        if size_labels:
            size_data['sizes'] = self._structure_size_data(size_labels, measurements)
            size_data['size_measurements'] = self._extract_size_specific_measurements(text, size_labels)
        
        return size_data
    
    def _extract_measurements(self, text: str) -> Dict[str, float]:
        """텍스트에서 측정값을 추출합니다."""
        measurements = {}
        
        # 텍스트를 소문자로 변환
        text_lower = text.lower()
        
        # 측정 항목별 패턴 매칭
        patterns = {
            'chest': r'(?:가슴|chest|bust).*?(\d+(?:\.\d+)?)',
            'waist': r'(?:허리|waist).*?(\d+(?:\.\d+)?)',
            'hip': r'(?:엉덩이|hip).*?(\d+(?:\.\d+)?)',
            'shoulder': r'(?:어깨|shoulder).*?(\d+(?:\.\d+)?)',
            'length': r'(?:길이|총장|기장|length).*?(\d+(?:\.\d+)?)',
            'sleeve': r'(?:소매|sleeve).*?(\d+(?:\.\d+)?)',
            'width': r'(?:폭|너비|width).*?(\d+(?:\.\d+)?)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = float(match.group(1))
                    # 합리적인 범위 체크 (10cm ~ 200cm)
                    if 10 <= value <= 200:
                        measurements[key] = value
                except ValueError:
                    pass
        
        # 테이블 형식 데이터 처리
        measurements.update(self._extract_table_data(text))
        
        return measurements
    
    def _extract_table_data(self, text: str) -> Dict[str, float]:
        """테이블 형식의 데이터를 추출합니다."""
        measurements = {}
        
        # 연속된 숫자들을 찾아서 테이블 데이터로 추정
        lines = text.split('\n')
        numbers = []
        
        for line in lines:
            # 숫자만 포함된 라인 찾기
            if re.match(r'^[\d\s\.]+$', line.strip()):
                line_numbers = re.findall(r'\d+(?:\.\d+)?', line)
                for num_str in line_numbers:
                    try:
                        numbers.append(float(num_str))
                    except ValueError:
                        pass
        
        # 발견된 숫자들을 측정값으로 추정
        if numbers:
            # 일반적인 의류 측정값 순서 추정
            if len(numbers) >= 1:
                if 30 <= numbers[0] <= 150:  # 가슴/폭
                    measurements['chest'] = numbers[0]
            if len(numbers) >= 2:
                if 30 <= numbers[1] <= 150:  # 길이
                    measurements['length'] = numbers[1]
            if len(numbers) >= 3:
                if 20 <= numbers[2] <= 100:  # 어깨
                    measurements['shoulder'] = numbers[2]
            if len(numbers) >= 4:
                if 20 <= numbers[3] <= 100:  # 소매
                    measurements['sleeve'] = numbers[3]
        
        return measurements
    
    def _extract_size_specific_measurements(self, text: str, size_labels: List[str]) -> Dict[str, Dict[str, float]]:
        """텍스트에서 사이즈별 측정값을 추출합니다."""
        size_measurements = {}
        
        # 텍스트를 라인별로 분리
        lines = text.split('\n')
        
        # 각 사이즈에 대해 측정값 찾기
        for size in size_labels:
            size_measurements[size] = {}
            
            # 해당 사이즈가 포함된 라인 찾기
            for line in lines:
                line_upper = line.upper()
                if size in line_upper:
                    # 측정값 패턴 찾기
                    measurements = self._extract_measurements_from_line(line)
                    if measurements:
                        size_measurements[size].update(measurements)
        
        return size_measurements
    
    def _extract_measurements_from_line(self, line: str) -> Dict[str, float]:
        """한 라인에서 측정값을 추출합니다."""
        measurements = {}
        
        # 측정 항목별 패턴 매칭
        patterns = {
            'chest': r'(?:가슴|chest|bust).*?(\d+(?:\.\d+)?)',
            'waist': r'(?:허리|waist).*?(\d+(?:\.\d+)?)',
            'hip': r'(?:엉덩이|hip).*?(\d+(?:\.\d+)?)',
            'shoulder': r'(?:어깨|shoulder).*?(\d+(?:\.\d+)?)',
            'length': r'(?:길이|총장|기장|length).*?(\d+(?:\.\d+)?)',
            'sleeve': r'(?:소매|sleeve).*?(\d+(?:\.\d+)?)',
            'width': r'(?:폭|너비|width).*?(\d+(?:\.\d+)?)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    # 합리적인 범위 체크 (10cm ~ 200cm)
                    if 10 <= value <= 200:
                        measurements[key] = value
                except ValueError:
                    pass
        
        return measurements
    
    def _structure_size_data(self, size_labels: List[str], measurements: Dict[str, float]) -> Dict[str, Dict]:
        """사이즈별로 데이터를 구조화합니다."""
        structured = {}
        
        # 각 사이즈에 대해 기본 측정값 할당
        for size in size_labels:
            structured[size] = measurements.copy()
            
            # 사이즈별 조정 (추정)
            size_adjustment = self._get_size_adjustment(size)
            for key in structured[size]:
                structured[size][key] *= size_adjustment
        
        return structured
    
    def _get_size_adjustment(self, size: str) -> float:
        """사이즈에 따른 조정 계수를 반환합니다."""
        adjustments = {
            'XS': 0.9,
            'S': 0.95,
            'M': 1.0,
            'L': 1.05,
            'XL': 1.1,
            'XXL': 1.15,
            'XXXL': 1.2,
            'FREE': 1.0
        }
        return adjustments.get(size.upper(), 1.0)
    
    def extract_size_from_chart(self, image_path: str) -> Dict[str, Any]:
        """사이즈 차트 이미지에서 사이즈 정보를 추출하는 메인 함수"""
        # OCR 수행
        text = self.extract_text_from_image(image_path)
        
        if not text:
            return {
                'success': False,
                'error': 'OCR 결과가 없습니다.',
                'raw_text': '',
                'measurements': {}
            }
        
        # 사이즈 정보 파싱
        size_data = self.parse_size_chart(text)
        
        # 결과 포맷팅
        result = {
            'success': True,
            'raw_text': size_data['raw_text'],
            'measurements': size_data['measurements'],
            'sizes': size_data.get('sizes', {}),
            'size_options': size_data.get('size_options', []),
            'size_measurements': size_data.get('size_measurements', {}),
            'confidence': self._calculate_confidence(size_data)
        }
        
        return result
    
    def _calculate_confidence(self, size_data: Dict[str, Any]) -> float:
        """추출된 데이터의 신뢰도를 계산합니다."""
        confidence = 0.0
        
        # 측정값이 있으면 신뢰도 증가
        if size_data['measurements']:
            confidence += 0.5
            # 주요 측정값이 있으면 추가 증가
            key_measurements = ['chest', 'length', 'waist', 'shoulder']
            for key in key_measurements:
                if key in size_data['measurements']:
                    confidence += 0.1
        
        # 사이즈 라벨이 있으면 신뢰도 증가
        if size_data.get('sizes'):
            confidence += 0.2
        
        # 텍스트가 충분히 있으면 신뢰도 증가
        if len(size_data['raw_text']) > 50:
            confidence += 0.1
        
        return min(confidence, 1.0)

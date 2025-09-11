#!/usr/bin/env python3
"""
AI 기반 가상 피팅 테스트
최신 AI 기술을 활용한 현실적인 피팅 결과 생성
"""

import json
import os
from virtual_fitting_ai import AIVirtualFitting
from config import settings
import time

def compare_all_methods():
    """모든 피팅 방법 비교"""
    
    # 테스트용 데이터 찾기
    models_dir = settings.MODELS_DIR
    clothes_dir = settings.CLOTHES_DIR
    
    model_files = [f for f in os.listdir(models_dir) if f.endswith('_data.json')]
    clothing_files = [f for f in os.listdir(clothes_dir) if f.endswith('_data.json')]
    
    if not model_files or not clothing_files:
        print("❌ 테스트할 데이터가 없습니다.")
        return
    
    # 데이터 로드
    model_data_path = os.path.join(models_dir, model_files[0])
    clothing_data_path = os.path.join(clothes_dir, clothing_files[0])
    
    with open(model_data_path, 'r') as f:
        model_data = json.load(f)
    
    # 옷 데이터 로드 (수정 가능성을 위해 복사본 사용)
    with open(clothing_data_path, 'r') as f:
        original_clothing_data = json.load(f)
    
    print("="*60)
    print("🎯 가상 피팅 시스템 비교 테스트")
    print("="*60)
    print(f"모델: {model_files[0]}")
    print(f"옷: {clothing_files[0]} (원본)")
    print()
    
    results = {}
    
    # 1. AI 기반 피팅 (기본 옷 데이터 사용)
    print("1️⃣ AI 기반 피팅 (기본 옷 치수)...")
    ai_fitting_default = AIVirtualFitting()
    clothing_data_default = original_clothing_data.copy()
    start_time = time.time()
    try:
        ai_result_default = ai_fitting_default.generate_fitting(model_data, clothing_data_default)
        ai_time_default = time.time() - start_time
        results['ai_default'] = {
            'path': ai_result_default,
            'time': ai_time_default,
            'status': '✅ 성공'
        }
        info_path = ai_result_default.replace('.jpg', '.jpg_info.json')
        if os.path.exists(info_path):
            with open(info_path, 'r') as f: info = json.load(f)
            print(f"   품질 점수: {info.get('quality_score', 0):.1f}%")
        print(f"   완료! (처리 시간: {ai_time_default:.2f}초)")
    except Exception as e:
        results['ai_default'] = {'status': f'❌ 실패: {e}'}
        print(f"   실패: {e}")
    
    print()
    
    # 2. AI 기반 피팅 (사이즈 차트 & 특정 사이즈 선택)
    print("2️⃣ AI 기반 피팅 (사이즈 차트: Large 선택)...")
    clothing_data_large = original_clothing_data.copy()
    # 테스트를 위한 사이즈 차트 데이터 추가 (실제 OCR 결과와 유사하게)
    clothing_data_large["available_sizes"] = {
        "Small": {"chest": 45.0, "waist": 40.0, "length": 60.0, "shoulder": 38.0},
        "Medium": {"chest": 50.0, "waist": 45.0, "length": 65.0, "shoulder": 42.0},
        "Large": {"chest": 55.0, "waist": 50.0, "length": 70.0, "shoulder": 46.0}
    }
    clothing_data_large["measurements"] = clothing_data_large["available_sizes"]["Large"]
    clothing_data_large["selected_size"] = "Large"
    
    ai_fitting_large = AIVirtualFitting()
    start_time = time.time()
    try:
        ai_result_large = ai_fitting_large.generate_fitting(model_data, clothing_data_large)
        ai_time_large = time.time() - start_time
        results['ai_large'] = {
            'path': ai_result_large,
            'time': ai_time_large,
            'status': '✅ 성공'
        }
        info_path = ai_result_large.replace('.jpg', '.jpg_info.json')
        if os.path.exists(info_path):
            with open(info_path, 'r') as f: info = json.load(f)
            print(f"   품질 점수: {info.get('quality_score', 0):.1f}%")
            print(f"   사용된 사이즈: {info.get('clothing_data', {}).get('selected_size', 'N/A')}")
            print(f"   사용된 치수: {info.get('clothing_data', {}).get('measurements', 'N/A')}")
        print(f"   완료! (처리 시간: {ai_time_large:.2f}초)")
    except Exception as e:
        results['ai_large'] = {'status': f'❌ 실패: {e}'}
        print(f"   실패: {e}")
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 결과 요약")
    print("="*60)
    
    print("\n| 방법         | 상태   | 처리 시간 | 품질 점수 | 사용된 사이즈 | 결과 파일 |")
    print("|--------------|--------|-----------|-----------|---------------|-----------|")
    
    for method, data in results.items():
        status = data.get('status', '?')
        time_str = f"{data.get('time', 0):.2f}초" if 'time' in data else '-'
        path = os.path.basename(data.get('path', '-')) if 'path' in data else '-'
        quality_score = "N/A"
        selected_size_display = "N/A"
        
        if method == 'ai_default':
            info_path = data.get('path', '').replace('.jpg', '.jpg_info.json')
            if os.path.exists(info_path):
                with open(info_path, 'r') as f: info = json.load(f)
                quality_score = f"{info.get('quality_score', 0):.1f}%"
                selected_size_display = info.get('clothing_data', {}).get('selected_size', '기본')
        elif method == 'ai_large':
            info_path = data.get('path', '').replace('.jpg', '.jpg_info.json')
            if os.path.exists(info_path):
                with open(info_path, 'r') as f: info = json.load(f)
                quality_score = f"{info.get('quality_score', 0):.1f}%"
                selected_size_display = info.get('clothing_data', {}).get('selected_size', 'Large')
        
        print(f"| {method:12} | {status:6} | {time_str:9} | {quality_score:9} | {selected_size_display:13} | {path} |")
    
    print("\n✨ 결과 이미지는 'results' 폴더에서 확인하세요!")

def main():
    print("🤖 AI 가상 피팅 시스템 테스트")
    print("최신 AI 기술로 더 현실적인 피팅 결과를 생성합니다.\n")
    
    # 디렉토리 생성
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    
    # 비교 테스트
    compare_all_methods()

if __name__ == "__main__":
    main()

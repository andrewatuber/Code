#!/usr/bin/env python3
"""
AI 기반 가상 피팅 테스트
최신 AI 기술을 활용한 현실적인 피팅 결과 생성
"""

import json
import os
from virtual_fitting import VirtualFitting
from virtual_fitting_advanced import AdvancedVirtualFitting
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
    
    with open(clothing_data_path, 'r') as f:
        clothing_data = json.load(f)
    
    print("="*60)
    print("🎯 가상 피팅 시스템 비교 테스트")
    print("="*60)
    print(f"모델: {model_files[0]}")
    print(f"옷: {clothing_files[0]}")
    print()
    
    results = {}
    
    # 1. 기본 피팅
    print("1️⃣ 기본 가상 피팅...")
    basic_fitting = VirtualFitting()
    start_time = time.time()
    try:
        basic_result = basic_fitting.generate_fitting(model_data, clothing_data)
        basic_time = time.time() - start_time
        results['basic'] = {
            'path': basic_result,
            'time': basic_time,
            'status': '✅ 성공'
        }
        print(f"   완료! (처리 시간: {basic_time:.2f}초)")
    except Exception as e:
        results['basic'] = {'status': f'❌ 실패: {e}'}
        print(f"   실패: {e}")
    
    print()
    
    # 2. 향상된 피팅
    print("2️⃣ 향상된 가상 피팅...")
    advanced_fitting = AdvancedVirtualFitting()
    start_time = time.time()
    try:
        advanced_result = advanced_fitting.generate_fitting(model_data, clothing_data)
        advanced_time = time.time() - start_time
        results['advanced'] = {
            'path': advanced_result,
            'time': advanced_time,
            'status': '✅ 성공'
        }
        print(f"   완료! (처리 시간: {advanced_time:.2f}초)")
        
        # 피팅 점수 읽기
        info_path = advanced_result + "_info.json"
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                info = json.load(f)
                if 'fit_analysis' in info and 'fit_score' in info['fit_analysis']:
                    print(f"   피팅 점수: {info['fit_analysis']['fit_score']}%")
    except Exception as e:
        results['advanced'] = {'status': f'❌ 실패: {e}'}
        print(f"   실패: {e}")
    
    print()
    
    # 3. AI 기반 피팅
    print("3️⃣ AI 기반 최첨단 가상 피팅...")
    ai_fitting = AIVirtualFitting()
    start_time = time.time()
    try:
        ai_result = ai_fitting.generate_fitting(model_data, clothing_data)
        ai_time = time.time() - start_time
        results['ai'] = {
            'path': ai_result,
            'time': ai_time,
            'status': '✅ 성공'
        }
        print(f"   완료! (처리 시간: {ai_time:.2f}초)")
        
        # 품질 점수 읽기
        info_path = ai_result + "_info.json"
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                info = json.load(f)
                if 'quality_score' in info:
                    print(f"   품질 점수: {info['quality_score']:.1f}%")
    except Exception as e:
        results['ai'] = {'status': f'❌ 실패: {e}'}
        print(f"   실패: {e}")
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 결과 요약")
    print("="*60)
    
    print("\n| 방법 | 상태 | 처리 시간 | 결과 파일 |")
    print("|------|------|-----------|-----------|")
    
    for method, data in results.items():
        status = data.get('status', '?')
        time_str = f"{data.get('time', 0):.2f}초" if 'time' in data else '-'
        path = os.path.basename(data.get('path', '-')) if 'path' in data else '-'
        print(f"| {method:8} | {status} | {time_str:9} | {path} |")
    
    print("\n💡 특징 비교:")
    print("• 기본: 빠른 처리, 기본적인 합성")
    print("• 향상된: 3D 워핑, 조명 매칭, 피팅 분석")
    print("• AI: 지능형 워핑, 고급 블렌딩, 품질 평가")
    
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

#!/usr/bin/env python3
"""
향상된 가상 피팅 테스트 스크립트
기존 방식과 향상된 방식의 결과를 비교합니다.
"""

import json
import os
from virtual_fitting import VirtualFitting
from virtual_fitting_advanced import AdvancedVirtualFitting
from config import settings

def test_fitting_comparison():
    """기본 피팅과 향상된 피팅을 비교 테스트"""
    
    # 테스트용 모델과 옷 데이터 찾기
    models_dir = settings.MODELS_DIR
    clothes_dir = settings.CLOTHES_DIR
    
    # 사용 가능한 모델 찾기
    model_files = [f for f in os.listdir(models_dir) if f.endswith('_data.json')]
    if not model_files:
        print("❌ 테스트할 모델 데이터가 없습니다. 먼저 모델을 업로드해주세요.")
        return
    
    # 사용 가능한 옷 찾기
    clothing_files = [f for f in os.listdir(clothes_dir) if f.endswith('_data.json')]
    if not clothing_files:
        print("❌ 테스트할 옷 데이터가 없습니다. 먼저 옷을 업로드해주세요.")
        return
    
    # 첫 번째 모델과 옷 사용
    model_data_path = os.path.join(models_dir, model_files[0])
    clothing_data_path = os.path.join(clothes_dir, clothing_files[0])
    
    print(f"📊 테스트 데이터:")
    print(f"   모델: {model_files[0]}")
    print(f"   옷: {clothing_files[0]}")
    print()
    
    # 데이터 로드
    with open(model_data_path, 'r') as f:
        model_data = json.load(f)
    
    with open(clothing_data_path, 'r') as f:
        clothing_data = json.load(f)
    
    # 기본 피팅 생성
    print("🔄 기본 가상 피팅 생성 중...")
    basic_fitting = VirtualFitting()
    try:
        basic_result = basic_fitting.generate_fitting(model_data, clothing_data)
        print(f"✅ 기본 피팅 완료: {basic_result}")
    except Exception as e:
        print(f"❌ 기본 피팅 실패: {e}")
        basic_result = None
    
    print()
    
    # 향상된 피팅 생성
    print("🚀 향상된 가상 피팅 생성 중...")
    advanced_fitting = AdvancedVirtualFitting()
    try:
        advanced_result = advanced_fitting.generate_fitting(model_data, clothing_data)
        print(f"✅ 향상된 피팅 완료: {advanced_result}")
        
        # 피팅 분석 정보 읽기
        info_path = advanced_result + "_info.json"
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                fit_info = json.load(f)
                
            print("\n📈 피팅 분석 결과:")
            print(f"   전체 피팅 점수: {fit_info['fit_analysis']['fit_score']}%")
            print(f"   전체 상태: {fit_info['fit_analysis']['overall_fit']}")
            
            print("\n   세부 분석:")
            for part, details in fit_info['fit_analysis']['details'].items():
                print(f"   - {part}: {details['status']} (비율: {details['fit_ratio']})")
            
            if fit_info['fit_analysis']['recommendations']:
                print("\n   추천사항:")
                for rec in fit_info['fit_analysis']['recommendations']:
                    print(f"   • {rec}")
            
            print("\n   적용된 고급 기능:")
            for feature, enabled in fit_info['advanced_features'].items():
                if enabled:
                    print(f"   ✓ {feature}")
    
    except Exception as e:
        print(f"❌ 향상된 피팅 실패: {e}")
        advanced_result = None
    
    print("\n" + "="*50)
    print("📊 비교 결과:")
    print("="*50)
    
    if basic_result and advanced_result:
        print("✅ 두 가지 피팅 모두 성공적으로 생성되었습니다!")
        print(f"\n기본 피팅 결과: {basic_result}")
        print(f"향상된 피팅 결과: {advanced_result}")
        print("\n💡 향상된 피팅의 주요 개선사항:")
        print("   • 더 정확한 신체 세그멘테이션")
        print("   • 3D 원근 변환으로 자연스러운 착용감")
        print("   • 조명과 색상 매칭으로 일관된 톤")
        print("   • 텍스처와 디테일 보존")
        print("   • 자연스러운 그림자 효과")
        print("   • 상세한 피팅 분석 및 점수")
    else:
        print("⚠️ 일부 피팅이 실패했습니다.")

def main():
    print("🎯 Virtual Fitting 향상된 기능 테스트")
    print("="*50)
    
    # 필요한 디렉토리 생성
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    
    # 비교 테스트 실행
    test_fitting_comparison()
    
    print("\n✨ 테스트 완료!")
    print("결과 이미지는 'results' 폴더에서 확인할 수 있습니다.")

if __name__ == "__main__":
    main()

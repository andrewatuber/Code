from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel
import aiofiles

from config import settings, create_directories
from body_measurement import BodyMeasurement
from clothing_analysis import ClothingAnalysis
from virtual_fitting import VirtualFitting
from virtual_fitting_advanced import AdvancedVirtualFitting
from virtual_fitting_ai import AIVirtualFitting
from ocr_service import OCRService

app = FastAPI(title="Virtual Fitting API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 필요한 디렉토리 생성
create_directories()

# 인스턴스 생성
body_measurement = BodyMeasurement()
clothing_analysis = ClothingAnalysis()
virtual_fitting = VirtualFitting()
advanced_fitting = AdvancedVirtualFitting()
ai_fitting = AIVirtualFitting()
ocr_service = OCRService()

class ModelData(BaseModel):
    height: float
    measurements: Dict[str, float]

class ClothingData(BaseModel):
    measurements: Dict[str, float]
    size_chart: Optional[Dict[str, Any]] = None

@app.post("/api/upload-model")
async def upload_model(
    image: UploadFile = File(...),
    height: float = Form(...)
):
    """모델 이미지와 키를 업로드하고 신체 치수를 계산"""
    try:
        # 이미지 저장
        filename = f"model_{image.filename}"
        file_path = os.path.join(settings.MODELS_DIR, filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await image.read()
            await f.write(content)
        
        # 신체 치수 계산
        measurements = body_measurement.calculate_measurements(file_path, height)
        
        # 결과 저장
        model_data = {
            "image_path": file_path,
            "height": height,
            "measurements": measurements
        }
        
        data_path = os.path.join(settings.MODELS_DIR, f"{filename}_data.json")
        async with aiofiles.open(data_path, 'w') as f:
            await f.write(json.dumps(model_data, ensure_ascii=False, indent=2))
        
        return {
            "success": True,
            "model_id": filename,
            "measurements": measurements
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-clothing")
async def upload_clothing(
    image: UploadFile = File(...),
    width: Optional[float] = Form(None),
    length: Optional[float] = Form(None),
    size_chart: Optional[str] = Form(None),
    clothing_type: Optional[str] = Form("shirt")
):
    """옷 이미지와 사이즈 정보를 업로드하고 치수를 분석"""
    try:
        # 이미지 저장
        filename = f"clothing_{image.filename}"
        file_path = os.path.join(settings.CLOTHES_DIR, filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await image.read()
            await f.write(content)
        
        # 사이즈 차트 파싱
        chart_data = None
        if size_chart:
            try:
                chart_data = json.loads(size_chart)
            except json.JSONDecodeError:
                pass
        
        # 옷 치수 분석
        measurements = clothing_analysis.analyze_clothing(
            file_path, width, length, chart_data
        )
        
        # 결과 저장
        clothing_data = {
            "image_path": file_path,
            "type": clothing_type,
            "width": width,
            "length": length,
            "size_chart": chart_data,
            "measurements": measurements
        }
        
        data_path = os.path.join(settings.CLOTHES_DIR, f"{filename}_data.json")
        async with aiofiles.open(data_path, 'w') as f:
            await f.write(json.dumps(clothing_data, ensure_ascii=False, indent=2))
        
        return {
            "success": True,
            "clothing_id": filename,
            "measurements": measurements
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/virtual-fitting")
async def create_virtual_fitting(
    model_id: str = Form(...),
    clothing_id: str = Form(...),
    use_advanced: bool = Form(False)
):
    """가상 피팅 이미지 생성"""
    try:
        # 모델 데이터 로드
        model_data_path = os.path.join(settings.MODELS_DIR, f"{model_id}_data.json")
        async with aiofiles.open(model_data_path, 'r') as f:
            model_data = json.loads(await f.read())
        
        # 옷 데이터 로드
        clothing_data_path = os.path.join(settings.CLOTHES_DIR, f"{clothing_id}_data.json")
        async with aiofiles.open(clothing_data_path, 'r') as f:
            clothing_data = json.loads(await f.read())
        
        # 가상 피팅 생성 (기본 또는 고급)
        if use_advanced:
            result_path = advanced_fitting.generate_fitting(
                model_data, clothing_data
            )
        else:
            result_path = virtual_fitting.generate_fitting(
                model_data, clothing_data
            )
        
        return {
            "success": True,
            "result_image": f"/api/result/{os.path.basename(result_path)}",
            "advanced_mode": use_advanced
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model or clothing data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/advanced-fitting")
async def create_advanced_fitting(
    model_id: str = Form(...),
    clothing_id: str = Form(...)
):
    """향상된 가상 피팅 이미지 생성 - 더 현실적인 결과"""
    try:
        # 모델 데이터 로드
        model_data_path = os.path.join(settings.MODELS_DIR, f"{model_id}_data.json")
        async with aiofiles.open(model_data_path, 'r') as f:
            model_data = json.loads(await f.read())
        
        # 옷 데이터 로드
        clothing_data_path = os.path.join(settings.CLOTHES_DIR, f"{clothing_id}_data.json")
        async with aiofiles.open(clothing_data_path, 'r') as f:
            clothing_data = json.loads(await f.read())
        
        # 향상된 가상 피팅 생성
        result_path = advanced_fitting.generate_fitting(
            model_data, clothing_data
        )
        
        # 피팅 분석 정보도 함께 반환
        info_path = result_path + "_info.json"
        fit_info = {}
        if os.path.exists(info_path):
            async with aiofiles.open(info_path, 'r') as f:
                fit_info = json.loads(await f.read())
        
        return {
            "success": True,
            "result_image": f"/api/result/{os.path.basename(result_path)}",
            "fit_analysis": fit_info.get("fit_analysis", {}),
            "advanced_features": fit_info.get("advanced_features", {})
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model or clothing data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/result/{filename}")
async def get_result_image(filename: str):
    """결과 이미지 반환"""
    file_path = os.path.join(settings.RESULTS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")

@app.get("/api/models")
async def list_models():
    """업로드된 모델 목록 반환"""
    models = []
    for filename in os.listdir(settings.MODELS_DIR):
        if filename.endswith("_data.json"):
            file_path = os.path.join(settings.MODELS_DIR, filename)
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                models.append({
                    "id": filename.replace("_data.json", ""),
                    "height": data["height"],
                    "measurements": data["measurements"]
                })
    return models

@app.post("/api/ocr-size-chart")
async def extract_size_from_chart(
    image: UploadFile = File(...)
):
    """사이즈 차트 이미지에서 OCR로 사이즈 정보를 추출"""
    try:
        # 임시 파일로 저장
        temp_filename = f"temp_ocr_{image.filename}"
        temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)
        
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await image.read()
            await f.write(content)
        
        # OCR 수행
        result = ocr_service.extract_size_from_chart(temp_path)
        
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            "success": result['success'],
            "raw_text": result.get('raw_text', ''),
            "measurements": result.get('measurements', {}),
            "sizes": result.get('sizes', {}),
            "confidence": result.get('confidence', 0)
        }
    
    except Exception as e:
        # 임시 파일 정리
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-fitting")
async def create_ai_fitting(
    model_id: str = Form(...),
    clothing_id: str = Form(...)
):
    """AI 기반 최첨단 가상 피팅 - 가장 현실적인 결과"""
    try:
        # 모델 데이터 로드
        model_data_path = os.path.join(settings.MODELS_DIR, f"{model_id}_data.json")
        async with aiofiles.open(model_data_path, 'r') as f:
            model_data = json.loads(await f.read())
        
        # 옷 데이터 로드
        clothing_data_path = os.path.join(settings.CLOTHES_DIR, f"{clothing_id}_data.json")
        async with aiofiles.open(clothing_data_path, 'r') as f:
            clothing_data = json.loads(await f.read())
        
        # AI 가상 피팅 생성
        result_path = ai_fitting.generate_fitting(
            model_data, clothing_data
        )
        
        # 피팅 분석 정보 로드
        info_path = result_path.replace('.jpg', '.jpg_info.json')
        quality_score = 0
        ai_features = {}
        
        if os.path.exists(info_path):
            async with aiofiles.open(info_path, 'r') as f:
                fit_info = json.loads(await f.read())
                quality_score = fit_info.get("quality_score", 0)
                ai_features = fit_info.get("ai_features", {})
        
        return {
            "success": True,
            "result_image": f"/api/result/{os.path.basename(result_path)}",
            "quality_score": quality_score,
            "ai_features": ai_features,
            "description": "AI 기반 최첨단 가상 피팅 결과"
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model or clothing data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clothes")
async def list_clothes():
    """업로드된 옷 목록 반환"""
    clothes = []
    for filename in os.listdir(settings.CLOTHES_DIR):
        if filename.endswith("_data.json"):
            file_path = os.path.join(settings.CLOTHES_DIR, filename)
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                clothes.append({
                    "id": filename.replace("_data.json", ""),
                    "measurements": data["measurements"]
                })
    return clothes

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
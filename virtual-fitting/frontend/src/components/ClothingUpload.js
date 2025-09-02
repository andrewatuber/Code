import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadClothing, extractSizeFromChart } from '../services/api';

const ClothingUpload = ({ onClothingUploaded }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [clothingType, setClothingType] = useState('shirt');
  const [width, setWidth] = useState('');
  const [length, setLength] = useState('');
  const [sizeChart, setSizeChart] = useState('');
  const [inputMethod, setInputMethod] = useState('dimensions'); // 'dimensions', 'size_chart', or 'ocr'
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [error, setError] = useState('');
  const [measurements, setMeasurements] = useState(null);
  const [ocrResult, setOcrResult] = useState(null);
  const [sizeChartImage, setSizeChartImage] = useState(null);
  const [selectedSize, setSelectedSize] = useState(''); // 선택된 사이즈
  const [showSizeSelector, setShowSizeSelector] = useState(false); // 사이즈 선택기 표시 여부

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      setError('');
    }
  }, []);

  const onSizeChartDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setSizeChartImage(file);
      setOcrLoading(true);
      setError('');
      setSelectedSize(''); // 사이즈 선택 초기화
      setShowSizeSelector(false);
      
      try {
        const result = await extractSizeFromChart(file);
        setOcrResult(result);
        
        // 사이즈 옵션이 있으면 사이즈 선택기 표시
        if (result.size_options && result.size_options.length > 0) {
          setShowSizeSelector(true);
          setSelectedSize(result.size_options[0]); // 첫 번째 사이즈를 기본값으로
        } else {
          // 사이즈 옵션이 없으면 일반 측정값 사용
          if (result.measurements) {
            const formattedText = Object.entries(result.measurements)
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n');
            setSizeChart(formattedText);
          }
          
          // 자동으로 폭과 길이 설정 (있는 경우)
          if (result.measurements.width) {
            setWidth(result.measurements.width.toString());
          }
          if (result.measurements.length) {
            setLength(result.measurements.length.toString());
          }
        }
      } catch (err) {
        setError('사이즈 차트 분석 실패: ' + err.message);
      } finally {
        setOcrLoading(false);
      }
    }
  }, []);

  // 선택된 사이즈가 변경될 때 해당 사이즈의 측정값으로 폼 업데이트
  useEffect(() => {
    if (selectedSize && ocrResult && ocrResult.size_measurements) {
      const sizeData = ocrResult.size_measurements[selectedSize];
      if (sizeData) {
        // 측정값을 사이즈 차트 텍스트로 변환
        const formattedText = Object.entries(sizeData)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        setSizeChart(formattedText);
        
        // 폭과 길이 설정
        if (sizeData.width) {
          setWidth(sizeData.width.toString());
        }
        if (sizeData.length) {
          setLength(sizeData.length.toString());
        }
      }
    }
  }, [selectedSize, ocrResult]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']
    },
    multiple: false
  });

  const { 
    getRootProps: getSizeChartRootProps, 
    getInputProps: getSizeChartInputProps, 
    isDragActive: isSizeChartDragActive 
  } = useDropzone({
    onDrop: onSizeChartDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']
    },
    multiple: false
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setError('이미지를 선택해주세요.');
      return;
    }

    if (inputMethod === 'dimensions' && !width && !length) {
      setError('폭 또는 길이 중 하나 이상을 입력해주세요.');
      return;
    }

    if (inputMethod === 'size_chart' && !sizeChart.trim()) {
      setError('사이즈 차트를 입력해주세요.');
      return;
    }

    if (inputMethod === 'ocr' && !ocrResult) {
      setError('먼저 사이즈 차트 이미지를 업로드해주세요.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let parsedSizeChart = null;
      
      if (inputMethod === 'ocr' && ocrResult) {
        if (selectedSize && ocrResult.size_measurements[selectedSize]) {
          // 선택된 사이즈의 측정값 사용
          parsedSizeChart = ocrResult.size_measurements[selectedSize];
        } else {
          // 일반 측정값 사용
          parsedSizeChart = ocrResult.measurements;
        }
      } else if (inputMethod === 'size_chart' && sizeChart.trim()) {
        try {
          parsedSizeChart = JSON.parse(sizeChart);
        } catch {
          // JSON이 아닌 경우 텍스트로 파싱 시도
          const lines = sizeChart.split('\n');
          parsedSizeChart = {};
          lines.forEach(line => {
            const [key, value] = line.split(':').map(s => s.trim());
            if (key && value) {
              parsedSizeChart[key] = value;
            }
          });
        }
      }

      const result = await uploadClothing(
        selectedFile,
        width ? parseFloat(width) : null,
        length ? parseFloat(length) : null,
        parsedSizeChart,
        clothingType
      );

      setMeasurements(result.measurements);
      onClothingUploaded({
        id: result.clothing_id,
        type: clothingType,
        measurements: result.measurements,
        image: selectedFile,
        width: width ? parseFloat(width) : null,
        length: length ? parseFloat(length) : null,
        sizeChart: parsedSizeChart,
        selectedSize: selectedSize || null
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setClothingType('shirt');
    setWidth('');
    setLength('');
    setSizeChart('');
    setError('');
    setMeasurements(null);
    setOcrResult(null);
    setSizeChartImage(null);
    setSelectedSize('');
    setShowSizeSelector(false);
  };

  return (
    <div className="card">
      <h2>옷 업로드</h2>
      <p className="text-muted">옷 사진과 사이즈 정보를 입력하여 치수를 분석합니다.</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">옷 사진</label>
          <div 
            {...getRootProps()} 
            className={`dropzone ${isDragActive ? 'active' : ''}`}
          >
            <input {...getInputProps()} />
            {selectedFile ? (
              <div>
                <p>✅ {selectedFile.name}</p>
                <p className="text-muted">다른 파일을 선택하려면 클릭하거나 드래그하세요</p>
              </div>
            ) : (
              <div>
                <p>👕 이미지를 드래그하거나 클릭하여 선택하세요</p>
                <p className="text-muted">JPG, PNG 파일만 지원됩니다</p>
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">옷 종류</label>
          <select
            className="form-input"
            value={clothingType}
            onChange={(e) => setClothingType(e.target.value)}
          >
            <option value="shirt">상의 (티셔츠, 블라우스, 셔츠)</option>
            <option value="pants">하의 (바지, 치마)</option>
            <option value="dress">원피스</option>
            <option value="jacket">자켓, 코트</option>
            <option value="sweater">니트, 스웨터</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">사이즈 입력 방법</label>
          <div className="input-method-selector">
            <label className="radio-option">
              <input
                type="radio"
                value="dimensions"
                checked={inputMethod === 'dimensions'}
                onChange={(e) => setInputMethod(e.target.value)}
              />
              <span>치수 직접 입력</span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                value="size_chart"
                checked={inputMethod === 'size_chart'}
                onChange={(e) => setInputMethod(e.target.value)}
              />
              <span>사이즈 차트 텍스트</span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                value="ocr"
                checked={inputMethod === 'ocr'}
                onChange={(e) => setInputMethod(e.target.value)}
              />
              <span>📷 사이즈 차트 이미지 (OCR)</span>
            </label>
          </div>
        </div>

        {inputMethod === 'dimensions' && (
          <>
            <div className="form-group">
              <label className="form-label" htmlFor="width">폭 (cm)</label>
              <input
                type="number"
                id="width"
                className="form-input"
                value={width}
                onChange={(e) => setWidth(e.target.value)}
                placeholder="예: 50"
                min="0"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="length">길이 (cm)</label>
              <input
                type="number"
                id="length"
                className="form-input"
                value={length}
                onChange={(e) => setLength(e.target.value)}
                placeholder="예: 65"
                min="0"
                step="0.1"
              />
            </div>
          </>
        )}

        {inputMethod === 'size_chart' && (
          <div className="form-group">
            <label className="form-label" htmlFor="sizeChart">사이즈 차트</label>
            <textarea
              id="sizeChart"
              className="form-input"
              value={sizeChart}
              onChange={(e) => setSizeChart(e.target.value)}
              placeholder="예:&#10;가슴둘레: 50&#10;허리둘레: 45&#10;총길이: 65&#10;&#10;또는 JSON 형식:&#10;{&quot;chest&quot;: 50, &quot;waist&quot;: 45, &quot;length&quot;: 65}"
              rows="6"
            />
          </div>
        )}

        {inputMethod === 'ocr' && (
          <div className="ocr-upload-section">
            <h4>
              📸 사이즈 차트 이미지 업로드
              {ocrLoading && <span className="spinner" style={{ marginLeft: '10px' }}></span>}
            </h4>
            <p className="text-muted">
              사이즈 차트가 포함된 이미지를 업로드하면 자동으로 사이즈 정보를 추출합니다.
            </p>
            
            <div 
              {...getSizeChartRootProps()} 
              className={`dropzone ${isSizeChartDragActive ? 'active' : ''}`}
              style={{ marginTop: '16px' }}
            >
              <input {...getSizeChartInputProps()} />
              {sizeChartImage ? (
                <div>
                  <p>✅ {sizeChartImage.name}</p>
                  <p className="text-muted">다른 파일을 선택하려면 클릭하거나 드래그하세요</p>
                </div>
              ) : (
                <div>
                  <p>📊 사이즈 차트 이미지를 업로드하세요</p>
                  <p className="text-muted">테이블이나 차트 형식의 이미지를 지원합니다</p>
                </div>
              )}
            </div>

            {ocrResult && (
              <div className="ocr-result">
                <h5>🔍 OCR 분석 결과</h5>
                {ocrResult.confidence && (
                  <p className="text-muted">신뢰도: {(ocrResult.confidence * 100).toFixed(0)}%</p>
                )}
                
                {ocrResult.measurements && Object.keys(ocrResult.measurements).length > 0 ? (
                  <div className="measurements-grid" style={{ marginTop: '16px' }}>
                    {Object.entries(ocrResult.measurements).map(([key, value]) => (
                      <div key={key} className="measurement-item">
                        <div className="measurement-label">
                          {getClothingMeasurementLabel(key)}
                        </div>
                        <div className="measurement-value">
                          {typeof value === 'number' ? `${value} cm` : value}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted">사이즈 정보를 찾을 수 없습니다. 다른 이미지를 시도해보세요.</p>
                )}
                
                {ocrResult.raw_text && (
                  <details style={{ marginTop: '16px' }}>
                    <summary style={{ cursor: 'pointer', color: '#667eea', fontWeight: 600 }}>
                      원본 텍스트 보기
                    </summary>
                    <div className="ocr-text">
                      {ocrResult.raw_text}
                    </div>
                  </details>
                )}
              </div>
            )}

            {showSizeSelector && ocrResult && ocrResult.size_options && (
              <div className="form-group">
                <label className="form-label">사이즈 선택</label>
                <div className="size-selector-info">
                  <p className="text-muted">
                    OCR에서 감지된 사이즈 옵션 중 하나를 선택하세요.
                  </p>
                </div>
                <select
                  className="form-input"
                  value={selectedSize}
                  onChange={(e) => setSelectedSize(e.target.value)}
                >
                  {ocrResult.size_options.map(option => (
                    <option key={option} value={option}>
                      {option} - {ocrResult.size_measurements[option] ? 
                        Object.entries(ocrResult.size_measurements[option])
                          .map(([key, value]) => `${getClothingMeasurementLabel(key)}: ${value}cm`)
                          .join(', ') : '측정값 없음'}
                    </option>
                  ))}
                </select>
                {selectedSize && ocrResult.size_measurements[selectedSize] && (
                  <div className="selected-size-details">
                    <h5>선택된 사이즈 ({selectedSize}) 상세 정보:</h5>
                    <div className="measurements-grid" style={{ marginTop: '12px' }}>
                      {Object.entries(ocrResult.size_measurements[selectedSize]).map(([key, value]) => (
                        <div key={key} className="measurement-item">
                          <div className="measurement-label">
                            {getClothingMeasurementLabel(key)}
                          </div>
                          <div className="measurement-value">
                            {typeof value === 'number' ? `${value} cm` : value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <div className="form-actions">
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={loading || !selectedFile}
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                분석 중...
              </>
            ) : (
              '옷 치수 분석'
            )}
          </button>
          
          {selectedFile && (
            <button 
              type="button" 
              className="btn btn-secondary"
              onClick={resetForm}
            >
              초기화
            </button>
          )}
        </div>
      </form>

      {measurements && (
        <div className="measurements-result">
          <h3>분석된 옷 치수</h3>
          <div className="measurements-grid">
            {Object.entries(measurements).map(([key, value]) => (
              <div key={key} className="measurement-item">
                <div className="measurement-label">
                  {getClothingMeasurementLabel(key)}
                </div>
                <div className="measurement-value">
                  {typeof value === 'number' ? `${value} cm` : value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const getClothingMeasurementLabel = (key) => {
  const labels = {
    width: '폭',
    length: '길이',
    chest: '가슴',
    waist: '허리',
    hip: '엉덩이',
    shoulder: '어깨',
    sleeve: '소매',
    neck: '목',
    image_aspect_ratio: '비율',
    image_width_pixels: '이미지 폭',
    image_height_pixels: '이미지 높이'
  };
  return labels[key] || key;
};

export default ClothingUpload;
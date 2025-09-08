import React, { useState } from 'react';
import { createVirtualFitting, createAdvancedFitting } from '../services/api';

const VirtualFitting = ({ model, clothing, onFittingComplete }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [useAdvanced, setUseAdvanced] = useState(true); // 기본값을 향상된 모드로 설정

  const handleGenerateFitting = async () => {
    setLoading(true);
    setError('');

    try {
      const result = useAdvanced 
        ? await createAdvancedFitting(model.id, clothing.id)
        : await createVirtualFitting(model.id, clothing.id, false);
      onFittingComplete(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getFitPrediction = () => {
    if (!model.measurements || !clothing.measurements) return null;

    const predictions = [];
    
    // 가슴 비교
    if (model.measurements.chest_circumference && clothing.measurements.chest) {
      const ratio = clothing.measurements.chest / model.measurements.chest_circumference;
      if (ratio < 0.95) predictions.push({ part: '가슴', status: 'tight', ratio });
      else if (ratio > 1.15) predictions.push({ part: '가슴', status: 'loose', ratio });
      else predictions.push({ part: '가슴', status: 'good', ratio });
    }

    // 허리 비교
    if (model.measurements.waist_circumference && clothing.measurements.waist) {
      const ratio = clothing.measurements.waist / model.measurements.waist_circumference;
      if (ratio < 0.95) predictions.push({ part: '허리', status: 'tight', ratio });
      else if (ratio > 1.15) predictions.push({ part: '허리', status: 'loose', ratio });
      else predictions.push({ part: '허리', status: 'good', ratio });
    }

    return predictions;
  };

  const fitPredictions = getFitPrediction();

  return (
    <div className="card">
      <h2>가상 피팅</h2>
      <p className="text-muted">선택한 모델과 옷으로 가상 피팅을 생성합니다.</p>

      <div className="fitting-preview">
        <div className="preview-grid">
          <div className="preview-item">
            <h3>모델 정보</h3>
            <div className="model-info">
              <p><strong>키:</strong> {model.height} cm</p>
              <div className="measurements-summary">
                <h4>주요 치수</h4>
                {model.measurements && (
                  <div className="measurements-grid">
                    <div className="measurement-item">
                      <div className="measurement-label">가슴</div>
                      <div className="measurement-value">
                        {model.measurements.chest_circumference} cm
                      </div>
                    </div>
                    <div className="measurement-item">
                      <div className="measurement-label">허리</div>
                      <div className="measurement-value">
                        {model.measurements.waist_circumference} cm
                      </div>
                    </div>
                    <div className="measurement-item">
                      <div className="measurement-label">어깨</div>
                      <div className="measurement-value">
                        {model.measurements.shoulder_width} cm
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="preview-item">
            <h3>옷 정보</h3>
            <div className="clothing-info">
              {clothing.type && (
                <p><strong>종류:</strong> {getClothingTypeLabel(clothing.type)}</p>
              )}
              {clothing.width && <p><strong>폭:</strong> {clothing.width} cm</p>}
              {clothing.length && <p><strong>길이:</strong> {clothing.length} cm</p>}
              <div className="measurements-summary">
                <h4>분석된 치수</h4>
                {clothing.measurements && (
                  <div className="measurements-grid">
                    {Object.entries(clothing.measurements)
                      .filter(([key]) => ['chest', 'waist', 'width', 'length'].includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="measurement-item">
                          <div className="measurement-label">
                            {key === 'chest' ? '가슴' : 
                             key === 'waist' ? '허리' : 
                             key === 'width' ? '폭' : '길이'}
                          </div>
                          <div className="measurement-value">
                            {typeof value === 'number' ? `${value} cm` : value}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {fitPredictions && fitPredictions.length > 0 && (
          <div className="fit-prediction">
            <h3>예상 피팅 결과</h3>
            <div className="prediction-grid">
              {fitPredictions.map((prediction, index) => (
                <div key={index} className="prediction-item">
                  <div className="prediction-part">{prediction.part}</div>
                  <div className={`fit-status ${prediction.status}`}>
                    {prediction.status === 'tight' ? '타이트' :
                     prediction.status === 'loose' ? '여유있음' : '적당함'}
                  </div>
                  <div className="prediction-ratio">
                    비율: {prediction.ratio.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      <div className="fitting-options">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={useAdvanced}
            onChange={(e) => setUseAdvanced(e.target.checked)}
            disabled={loading}
          />
          <span>향상된 피팅 모드 사용 (더 현실적인 결과)</span>
        </label>
        <div className="mode-description">
          {useAdvanced ? (
            <p className="text-muted">
              ✨ 고급 기능: 3D 워핑, 신체 세그멘테이션, 조명 매칭, 텍스처 보존
            </p>
          ) : (
            <p className="text-muted">
              기본 모드: 빠른 처리 속도
            </p>
          )}
        </div>
      </div>

      <div className="fitting-actions">
        <button 
          className="btn btn-primary btn-large"
          onClick={handleGenerateFitting}
          disabled={loading}
        >
          {loading ? (
            <>
              <div className="spinner"></div>
              {useAdvanced ? '향상된 피팅 생성 중...' : '가상 피팅 생성 중...'}
            </>
          ) : (
            <>🎯 {useAdvanced ? '향상된 가상 피팅 생성' : '가상 피팅 생성'}</>
          )}
        </button>
      </div>

      {loading && (
        <div className="loading-info">
          <p>AI가 가상 피팅을 생성하고 있습니다...</p>
          <p className="text-muted">이 과정은 몇 초 정도 소요될 수 있습니다.</p>
        </div>
      )}
    </div>
  );
};

const getClothingTypeLabel = (type) => {
  const labels = {
    'shirt': '상의 (티셔츠, 블라우스, 셔츠)',
    'pants': '하의 (바지, 치마)',
    'dress': '원피스',
    'jacket': '자켓, 코트',
    'sweater': '니트, 스웨터'
  };
  return labels[type] || type;
};

export default VirtualFitting;
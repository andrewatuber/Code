import React, { useState, useEffect } from 'react';
import { getModels } from '../services/api';

const ModelList = ({ onModelSelected }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    setLoading(true);
    setError('');

    try {
      const modelsData = await getModels();
      setModels(modelsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h3>저장된 모델</h3>
        <div className="loading">
          <div className="spinner"></div>
          <p>모델 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3>저장된 모델</h3>
        <div className="error">{error}</div>
        <button className="btn btn-secondary" onClick={loadModels}>
          다시 시도
        </button>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="card">
        <h3>저장된 모델</h3>
        <div className="empty-state">
          <p>저장된 모델이 없습니다.</p>
          <p className="text-muted">새 모델을 업로드해보세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>저장된 모델</h3>
      <p className="text-muted">기존에 업로드한 모델을 선택할 수 있습니다.</p>
      
      <div className="model-list">
        {models.map((model) => (
          <div key={model.id} className="model-item">
            <div className="model-info">
              <div className="model-basic-info">
                <h4>모델 {model.id}</h4>
                <p><strong>키:</strong> {model.height} cm</p>
              </div>
              
              <div className="model-measurements">
                <h5>주요 치수</h5>
                <div className="measurements-mini-grid">
                  {model.measurements && (
                    <>
                      <div className="mini-measurement">
                        <span className="label">가슴:</span>
                        <span className="value">{model.measurements.chest_circumference} cm</span>
                      </div>
                      <div className="mini-measurement">
                        <span className="label">허리:</span>
                        <span className="value">{model.measurements.waist_circumference} cm</span>
                      </div>
                      <div className="mini-measurement">
                        <span className="label">어깨:</span>
                        <span className="value">{model.measurements.shoulder_width} cm</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <button 
              className="btn btn-primary"
              onClick={() => onModelSelected(model)}
            >
              이 모델 선택
            </button>
          </div>
        ))}
      </div>
      
      <button className="btn btn-secondary" onClick={loadModels}>
        🔄 새로고침
      </button>
    </div>
  );
};

export default ModelList;
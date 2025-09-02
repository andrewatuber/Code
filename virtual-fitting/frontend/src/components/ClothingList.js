import React, { useState, useEffect } from 'react';
import { getClothes } from '../services/api';

const ClothingList = ({ onClothingSelected }) => {
  const [clothes, setClothes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadClothes();
  }, []);

  const loadClothes = async () => {
    setLoading(true);
    setError('');

    try {
      const clothesData = await getClothes();
      setClothes(clothesData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h3>저장된 옷</h3>
        <div className="loading">
          <div className="spinner"></div>
          <p>옷 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3>저장된 옷</h3>
        <div className="error">{error}</div>
        <button className="btn btn-secondary" onClick={loadClothes}>
          다시 시도
        </button>
      </div>
    );
  }

  if (clothes.length === 0) {
    return (
      <div className="card">
        <h3>저장된 옷</h3>
        <div className="empty-state">
          <p>저장된 옷이 없습니다.</p>
          <p className="text-muted">새 옷을 업로드해보세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>저장된 옷</h3>
      <p className="text-muted">기존에 업로드한 옷을 선택할 수 있습니다.</p>
      
      <div className="clothing-list">
        {clothes.map((clothing) => (
          <div key={clothing.id} className="clothing-item">
            <div className="clothing-info">
              <div className="clothing-basic-info">
                <h4>옷 {clothing.id}</h4>
              </div>
              
              <div className="clothing-measurements">
                <h5>분석된 치수</h5>
                <div className="measurements-mini-grid">
                  {clothing.measurements && (
                    <>
                      {clothing.measurements.width && (
                        <div className="mini-measurement">
                          <span className="label">폭:</span>
                          <span className="value">{clothing.measurements.width} cm</span>
                        </div>
                      )}
                      {clothing.measurements.length && (
                        <div className="mini-measurement">
                          <span className="label">길이:</span>
                          <span className="value">{clothing.measurements.length} cm</span>
                        </div>
                      )}
                      {clothing.measurements.chest && (
                        <div className="mini-measurement">
                          <span className="label">가슴:</span>
                          <span className="value">{clothing.measurements.chest} cm</span>
                        </div>
                      )}
                      {clothing.measurements.waist && (
                        <div className="mini-measurement">
                          <span className="label">허리:</span>
                          <span className="value">{clothing.measurements.waist} cm</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <button 
              className="btn btn-primary"
              onClick={() => onClothingSelected(clothing)}
            >
              이 옷 선택
            </button>
          </div>
        ))}
      </div>
      
      <button className="btn btn-secondary" onClick={loadClothes}>
        🔄 새로고침
      </button>
    </div>
  );
};

export default ClothingList;
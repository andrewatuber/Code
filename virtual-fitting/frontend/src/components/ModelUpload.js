import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadModel } from '../services/api';

const ModelUpload = ({ onModelUploaded }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [height, setHeight] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [measurements, setMeasurements] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      setError('');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
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
    
    if (!height || height <= 0) {
      setError('올바른 키를 입력해주세요.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await uploadModel(selectedFile, parseFloat(height));
      setMeasurements(result.measurements);
      onModelUploaded({
        id: result.model_id,
        height: parseFloat(height),
        measurements: result.measurements,
        image: selectedFile
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setHeight('');
    setError('');
    setMeasurements(null);
  };

  return (
    <div className="card">
      <h2>모델 업로드</h2>
      <p className="text-muted">전신 사진과 키를 입력하여 신체 치수를 계산합니다.</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">전신 사진</label>
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
                <p>📷 이미지를 드래그하거나 클릭하여 선택하세요</p>
                <p className="text-muted">JPG, PNG 파일만 지원됩니다</p>
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="height">키 (cm)</label>
          <input
            type="number"
            id="height"
            className="form-input"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="예: 170"
            min="100"
            max="250"
            step="0.1"
          />
        </div>

        {error && <div className="error">{error}</div>}

        <div className="form-actions">
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={loading || !selectedFile || !height}
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                분석 중...
              </>
            ) : (
              '신체 치수 계산'
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
          <h3>계산된 신체 치수</h3>
          <div className="measurements-grid">
            {Object.entries(measurements).map(([key, value]) => (
              <div key={key} className="measurement-item">
                <div className="measurement-label">
                  {getMeasurementLabel(key)}
                </div>
                <div className="measurement-value">
                  {value} cm
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const getMeasurementLabel = (key) => {
  const labels = {
    shoulder_width: '어깨 너비',
    chest_circumference: '가슴 둘레',
    waist_circumference: '허리 둘레',
    hip_circumference: '엉덩이 둘레',
    arm_length: '팔 길이',
    leg_length: '다리 길이',
    torso_length: '상체 길이',
    neck_circumference: '목 둘레'
  };
  return labels[key] || key;
};

export default ModelUpload;
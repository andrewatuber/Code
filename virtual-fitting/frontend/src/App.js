import React, { useState } from 'react';
import ModelUpload from './components/ModelUpload';
import ClothingUpload from './components/ClothingUpload';
import VirtualFitting from './components/VirtualFitting';
import ModelList from './components/ModelList';
import ClothingList from './components/ClothingList';
import './App.css';

function App() {
  const [currentStep, setCurrentStep] = useState('upload-model');
  const [selectedModel, setSelectedModel] = useState(null);
  const [selectedClothing, setSelectedClothing] = useState(null);
  const [fittingResult, setFittingResult] = useState(null);

  const handleModelUploaded = (modelData) => {
    setSelectedModel(modelData);
    setCurrentStep('upload-clothing');
  };

  const handleClothingUploaded = (clothingData) => {
    setSelectedClothing(clothingData);
    setCurrentStep('virtual-fitting');
  };

  const handleFittingComplete = (result) => {
    setFittingResult(result);
    setCurrentStep('result');
  };

  const resetApp = () => {
    setCurrentStep('upload-model');
    setSelectedModel(null);
    setSelectedClothing(null);
    setFittingResult(null);
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="container">
          <h1>Virtual Fitting</h1>
          <p>AI 기반 가상 피팅 서비스</p>
        </div>
      </header>

      <main className="container">
        <div className="step-indicator">
          <div className={`step ${currentStep === 'upload-model' ? 'active' : ''} ${selectedModel ? 'completed' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">모델 업로드</span>
          </div>
          <div className={`step ${currentStep === 'upload-clothing' ? 'active' : ''} ${selectedClothing ? 'completed' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">옷 업로드</span>
          </div>
          <div className={`step ${currentStep === 'virtual-fitting' ? 'active' : ''} ${fittingResult ? 'completed' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">가상 피팅</span>
          </div>
          <div className={`step ${currentStep === 'result' ? 'active' : ''}`}>
            <span className="step-number">4</span>
            <span className="step-label">결과</span>
          </div>
        </div>

        {currentStep === 'upload-model' && (
          <div className="grid">
            <ModelUpload onModelUploaded={handleModelUploaded} />
            <ModelList onModelSelected={(model) => {
              setSelectedModel(model);
              setCurrentStep('upload-clothing');
            }} />
          </div>
        )}

        {currentStep === 'upload-clothing' && (
          <div className="grid">
            <ClothingUpload onClothingUploaded={handleClothingUploaded} />
            <ClothingList onClothingSelected={(clothing) => {
              setSelectedClothing(clothing);
              setCurrentStep('virtual-fitting');
            }} />
          </div>
        )}

        {currentStep === 'virtual-fitting' && (
          <VirtualFitting
            model={selectedModel}
            clothing={selectedClothing}
            onFittingComplete={handleFittingComplete}
          />
        )}

        {currentStep === 'result' && fittingResult && (
          <div className="card">
            <h2>가상 피팅 결과</h2>
            <div className="result-container">
              <img 
                src={`http://localhost:8000${fittingResult.result_image}`} 
                alt="Virtual Fitting Result" 
                className="result-image"
              />
              <div className="result-actions">
                <button className="btn btn-primary" onClick={resetApp}>
                  새로운 피팅 시작
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => setCurrentStep('upload-clothing')}
                >
                  다른 옷으로 피팅
                </button>
              </div>
            </div>
          </div>
        )}

        {currentStep !== 'upload-model' && (
          <div className="navigation">
            <button 
              className="btn btn-secondary" 
              onClick={() => {
                if (currentStep === 'upload-clothing') setCurrentStep('upload-model');
                else if (currentStep === 'virtual-fitting') setCurrentStep('upload-clothing');
                else if (currentStep === 'result') setCurrentStep('virtual-fitting');
              }}
            >
              이전 단계
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
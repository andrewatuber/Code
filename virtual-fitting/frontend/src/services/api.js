import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const uploadModel = async (imageFile, height) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('height', height);

  try {
    const response = await api.post('/upload-model', formData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || '모델 업로드에 실패했습니다.');
  }
};

export const uploadClothing = async (imageFile, width = null, length = null, sizeChart = null, clothingType = 'shirt') => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('clothing_type', clothingType);
  
  if (width) formData.append('width', width);
  if (length) formData.append('length', length);
  if (sizeChart) formData.append('size_chart', JSON.stringify(sizeChart)); // sizes 객체를 포함할 수 있음

  try {
    const response = await api.post('/upload-clothing', formData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || '옷 업로드에 실패했습니다.');
  }
};

export const createAIFitting = async (modelId, clothingId, selectedSize = null) => {
  const formData = new FormData();
  formData.append('model_id', modelId);
  formData.append('clothing_id', clothingId);
  if (selectedSize) formData.append('selected_size', selectedSize); // 선택된 사이즈 추가

  try {
    const response = await api.post('/ai-fitting', formData); // AI 피팅 엔드포인트 호출
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'AI 기반 가상 피팅 생성에 실패했습니다.');
  }
};

export const getModels = async () => {
  try {
    const response = await api.get('/models');
    return response.data;
  } catch (error) {
    throw new Error('모델 목록을 불러오는데 실패했습니다.');
  }
};

export const getClothes = async () => {
  try {
    const response = await api.get('/clothes');
    return response.data;
  } catch (error) {
    throw new Error('옷 목록을 불러오는데 실패했습니다.');
  }
};

export const extractSizeFromChart = async (imageFile) => {
  const formData = new FormData();
  formData.append('image', imageFile);

  try {
    const response = await api.post('/ocr-size-chart', formData);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || '사이즈 차트 분석에 실패했습니다.');
  }
};

export default api;
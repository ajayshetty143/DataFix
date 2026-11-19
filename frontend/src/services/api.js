import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for consistent error extraction
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = error.message;
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        message = error.response.data.detail;
      } else if (Array.isArray(error.response.data.detail)) {
        message = error.response.data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      }
    }
    const errorDetails = {
      message,
      status: error.response?.status,
      data: error.response?.data,
    };
    console.error('API Error:', errorDetails);
    return Promise.reject(errorDetails);
  }
);

export const healthApi = {
  getHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export const datasetApi = {
  uploadDataset: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percentCompleted);
        }
      },
    });
    return response.data;
  },

  getDataset: async (datasetId) => {
    const response = await apiClient.get(`/datasets/${datasetId}`);
    return response.data;
  },

  getPreview: async (datasetId, page = 1, pageSize = 20) => {
    const response = await apiClient.get(`/datasets/${datasetId}/preview`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  listDatasets: async (limit = 10) => {
    const response = await apiClient.get('/datasets', {
      params: { limit },
    });
    return response.data;
  },

  analyzeQuality: async (datasetId) => {
    const response = await apiClient.post(`/datasets/${datasetId}/analyze`);
    return response.data;
  },

  getQualityReport: async (datasetId) => {
    const response = await apiClient.get(`/datasets/${datasetId}/quality`);
    return response.data;
  },
};

export default apiClient;

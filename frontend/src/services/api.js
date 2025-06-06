import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 401 에러 시 로그아웃
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 인증 API
export const authApi = {
  login: (credentials) => api.post('/api/auth/login', credentials).then(res => res.data),
  register: (userData) => api.post('/api/auth/register', userData).then(res => res.data),
  getCurrentUser: () => api.get('/api/auth/me').then(res => res.data),
};

// 앱 API
export const appsApi = {
  getAll: () => api.get('/api/apps/').then(res => res.data),
  getById: (id) => api.get(`/api/apps/${id}`).then(res => res.data),
  create: (data) => api.post('/api/apps/', data).then(res => res.data),
  update: (id, data) => api.put(`/api/apps/${id}`, data).then(res => res.data),
  delete: (id) => api.delete(`/api/apps/${id}`).then(res => res.data),
  deploy: (id, data) => api.post(`/api/apps/${id}/deploy`, data).then(res => res.data),
  stop: (id) => api.post(`/api/apps/${id}/stop`).then(res => res.data),
  getLogs: (id) => api.get(`/api/apps/${id}/logs`).then(res => res.data),
};

// 배포 API
export const deploymentsApi = {
  getByAppId: (appId) => api.get(`/api/deployments/app/${appId}`).then(res => res.data),
};

// Git 인증 정보 API
export const gitCredentialsApi = {
  getAll: () => api.get('/api/git-credentials/').then(res => res.data),
  getById: (id) => api.get(`/api/git-credentials/${id}`).then(res => res.data),
  create: (data) => api.post('/api/git-credentials/', data).then(res => res.data),
  update: (id, data) => api.put(`/api/git-credentials/${id}`, data).then(res => res.data),
  delete: (id) => api.delete(`/api/git-credentials/${id}`).then(res => res.data),
};

export default api; 
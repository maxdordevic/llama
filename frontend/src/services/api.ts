import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat endpoints
export const sendMessage = (data: {
  message: string;
  user_id: string;
  session_id?: string;
  stream?: boolean;
  metadata?: any;
}) => {
  return api.post('/chat', data);
};

// Session endpoints
export const createSession = (data: {
  user_id: string;
  title?: string;
  metadata?: any;
}) => {
  return api.post('/sessions', data);
};

export const getSession = (sessionId: string) => {
  return api.get(`/sessions/${sessionId}`);
};

export const listUserSessions = (userId: string, params?: {
  limit?: number;
  offset?: number;
}) => {
  return api.get(`/users/${userId}/sessions`, { params });
};

export const deleteSession = (sessionId: string) => {
  return api.delete(`/sessions/${sessionId}`);
};

// Code execution
export const executeCode = (data: {
  code: string;
  context?: any;
  timeout?: number;
}) => {
  return api.post('/execute/code', data);
};

// Memory endpoints
export const addMemory = (data: {
  user_id: string;
  content: string;
  memory_type?: string;
  importance?: number;
  long_term?: boolean;
}) => {
  return api.post('/memory/add', data);
};

export const getUserMemory = (userId: string) => {
  return api.get(`/memory/${userId}`);
};

export const getUserPreferences = (userId: string) => {
  return api.get(`/memory/${userId}/preferences`);
};

// Task planning
export const createExecutionPlan = (data: { user_request: string }) => {
  return api.post('/plan/create', data);
};

// System
export const getProviders = () => {
  return api.get('/providers');
};

export const healthCheck = () => {
  return api.get('/health');
};

export default api;

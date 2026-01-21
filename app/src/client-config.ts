// src/client-config.ts
import axios from 'axios';
import type { CreateClientConfig } from './client/client.gen';

export const createClientConfig: CreateClientConfig = (config) => {
  const API_BASE_URL =
    import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const http = axios.create({
    baseURL: API_BASE_URL,
  });

  http.interceptors.response.use(
    (res) => res,
    (error) => {
      if (error?.response?.status === 401) {
        localStorage.removeItem('tb_access_token');
        localStorage.removeItem('tb_refresh_token');
        if (window.location.pathname !== '/admin/login') {
          window.location.href = '/admin/login';
        }
      }
      return Promise.reject(error);
    }
  );

  return {
    ...config,
    baseURL: API_BASE_URL,
    auth: () => localStorage.getItem('tb_access_token') || undefined,
    axios: http,
  };
};
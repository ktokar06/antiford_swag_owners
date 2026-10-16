import { apiFetch, setToken, clearToken } from './client';

export const authApi = {
  async login(email, password) {
    const data = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    if (data.access_token) setToken(data.access_token);
    return data;
  },

  async me() {
    return apiFetch('/api/auth/me');
  },

  async uploadAvatar(file) {
    const body = new FormData();
    body.append('file', file);
    return apiFetch('/api/auth/me/avatar', { method: 'POST', body });
  },

  async deleteAvatar() {
    return apiFetch('/api/auth/me/avatar', { method: 'DELETE' });
  },

  async changePassword(oldPassword, newPassword) {
    return apiFetch('/api/auth/change-password', {
      method: 'POST',
      body: { old_password: oldPassword, new_password: newPassword },
    });
  },

  async requestReset(email) {
    return apiFetch('/api/auth/forgot-password', {
      method: 'POST',
      body: { email },
    });
  },

  async resetPassword(token, newPassword) {
    return apiFetch('/api/auth/reset-password', {
      method: 'POST',
      body: { token, new_password: newPassword },
    });
  },

  logout() {
    clearToken();
    window.location.href = '/login';
  },
};

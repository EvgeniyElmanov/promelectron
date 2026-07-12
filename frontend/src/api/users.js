import api from '@/services/api';

/**
 * Upload a new avatar for the current user.
 *
 * @param {File} file
 * @param {(progressEvent: ProgressEvent) => void} [onUploadProgress]
 * @returns {Promise<import('axios').AxiosResponse<{ avatar_url: string, original: string, small: string, medium: string, large: string }>>}
 */
export function uploadAvatar(file, onUploadProgress) {
  const formData = new FormData();
  formData.append('file', file);

  return api.post('/me/avatar/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
}

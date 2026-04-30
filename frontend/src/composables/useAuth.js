import { jwtDecode } from 'jwt-decode';

export const useAuth = () => {
  const getToken = () => localStorage.getItem('access_token');

  const getUserRole = () => {
    const token = getToken();
    if (!token) return null;
    try {
      const decoded = jwtDecode(token);
      return decoded.role;
    } catch {
      return null;
    }
  };

  const isAdmin = () => getUserRole() === 'admin';
  const isSupplier = () => getUserRole() === 'supplier';
  const isAuthenticated = () => !!getToken();

  return {
    getToken,
    getUserRole,
    isAdmin,
    isSupplier,
    isAuthenticated,
  };
};

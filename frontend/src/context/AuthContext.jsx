import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { 
  login as apiLogin, 
  logout as apiLogout, 
  fetchCurrentUser, 
  getAuthToken, 
  clearAuthTokens 
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(getAuthToken());
  const [loading, setLoading] = useState(true);

  // Initialize and validate existing token on app load
  useEffect(() => {
    let isMounted = true;

    async function initializeAuth() {
      const storedToken = getAuthToken();
      if (!storedToken) {
        if (isMounted) setLoading(false);
        return;
      }

      try {
        const userProfile = await fetchCurrentUser();
        if (isMounted) {
          setUser(userProfile);
          setToken(storedToken);
        }
      } catch (err) {
        console.warn('Initial session validation failed:', err);
        clearAuthTokens();
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    initializeAuth();

    // Listen for 401 unauthorized events across any secure fetch call
    const handleUnauthorized = () => {
      clearAuthTokens();
      setUser(null);
      setToken(null);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    setToken(data.access_token);
    const profile = await fetchCurrentUser();
    setUser(profile);
    return profile;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setToken(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await fetchCurrentUser();
      setUser(profile);
      return profile;
    } catch (err) {
      console.error('Failed to refresh user profile:', err);
      throw err;
    }
  }, []);

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user && !!token,
    isAdmin: user?.role === 'ADMIN',
    isViewer: user?.role === 'VIEWER',
    login,
    logout,
    refreshProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

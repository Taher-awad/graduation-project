import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole } from '../types';
import type { User } from '../types';
import { jwtDecode } from "jwt-decode"; // You might need to install this: npm install jwt-decode

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<User | null>(null);

  const login = (newToken: string) => {
    setToken(newToken);
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('token');
  };

  useEffect(() => {
    if (token) {
        try {
            // Simple decode to get user info. 
            // In a real app, you might call /auth/me
            const decoded = jwtDecode<{ sub: string; role?: string }>(token);
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setUser({
                username: decoded.sub,
                role: (decoded.role as UserRole) || UserRole.STUDENT 
            });
            localStorage.setItem('token', token);
        } catch (e) {
            console.error("Invalid token", e);
            logout();
        }
    } else {
        localStorage.removeItem('token');
        setUser(null);
    }
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
};

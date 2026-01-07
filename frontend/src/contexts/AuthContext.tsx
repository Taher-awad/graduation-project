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

  useEffect(() => {
    if (token) {
        try {
            // Simple decode to get user info. 
            // In a real app, you might call /auth/me
            const decoded: any = jwtDecode(token);
            setUser({
                username: decoded.sub,
                role: decoded.role || UserRole.STUDENT 
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

  const login = (newToken: string) => {
    setToken(newToken);
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
};

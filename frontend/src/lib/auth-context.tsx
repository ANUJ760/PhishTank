import React, { createContext, useContext, useEffect, useState } from "react";
import { User } from "@/types/api";
import { api } from "./api-client";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, pwd: string) => Promise<User>;
  signUp: (name: string, email: string, pwd: string) => Promise<User>;
  signOut: () => Promise<void>;
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refetchUser = async () => {
    try {
      const me = await api.auth.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refetchUser();
  }, []);

  const signIn = async (email: string, pwd: string) => {
    const loggedInUser = await api.auth.signIn(email, pwd);
    setUser(loggedInUser);
    return loggedInUser;
  };

  const signUp = async (name: string, email: string, pwd: string) => {
    const newUser = await api.auth.signUp(name, email, pwd);
    setUser(newUser);
    return newUser;
  };

  const signOut = async () => {
    try {
      await api.auth.signOut();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signUp, signOut, refetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

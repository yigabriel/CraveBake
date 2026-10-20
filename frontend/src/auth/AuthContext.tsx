import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { setUnauthorizedHandler, tokenStore } from "../api/client";
import { authApi, usersApi } from "../api/endpoints";
import type { User } from "../api/types";
import { browserLanguage } from "../i18n";

interface AuthState {
  user: User | null;
  /** True while a stored token is being checked on first load. */
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, fullName: string) => Promise<User>;
  logout: () => void;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { i18n } = useTranslation();
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokenStore.get() !== null);

  const setUser = useCallback(
    (next: User) => {
      setUserState(next);
      // UI texts follow the user's preference...
      if (i18n.language !== next.preferred_language) {
        void i18n.changeLanguage(next.preferred_language);
        // ...and so do catalog names, which the API returns already translated: refetch what is cached.
        void queryClient.invalidateQueries();
      }
    },
    [i18n, queryClient],
  );

  const logout = useCallback(() => {
    tokenStore.set(null);
    setUserState(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    // Any 401 with a token (expired, revoked): drop the session; routes send to /login?next=.
    setUnauthorizedHandler(logout);
    if (!tokenStore.get()) return;
    usersApi
      .me()
      .then(setUser)
      .catch(() => logout())
      .finally(() => setLoading(false));
  }, [logout, setUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login(email, password);
      tokenStore.set(response.access_token);
      setUser(response.user);
      return response.user;
    },
    [setUser],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      // The account speaks the browser's language from the start.
      await authApi.register({ email, password, full_name: fullName, preferred_language: browserLanguage() });
      // Registration returns no token: sign in with the same credentials.
      return login(email, password);
    },
    [login],
  );

  const value = useMemo(
    () => ({ user, loading, login, register, logout, setUser }),
    [user, loading, login, register, logout, setUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** For pages that only render once signed in. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useUser needs a signed-in user");
  return user;
}

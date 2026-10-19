import { useRef, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { LogoMark } from "./components/Logo";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { ConverterPage } from "./pages/ConverterPage";
import { CookPage } from "./pages/CookPage";
import { DeckPage, DiscoverResultsPage, DiscoverStartPage } from "./pages/DiscoverPages";
import { ExplorePage } from "./pages/ExplorePage";
import { HistoryPage } from "./pages/HistoryPage";
import { KitchenPage } from "./pages/KitchenPage";
import { PantryPage } from "./pages/PantryPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RecipeDetailPage } from "./pages/RecipeDetailPage";
import { RecipeEditorPage } from "./pages/RecipeEditorPage";

function Splash() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <LogoMark size={72} className="animate-pulse" />
    </div>
  );
}

/** Signed-out users go to the login, remembering where they were going (§1). */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Splash />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <>{children}</>;
}

/**
 * Login/register are skipped only when already signed in on arrival. Signing in *here*
 * must not redirect: the page itself navigates (to ?next= or the onboarding), and a
 * redirect from this guard would race it and win.
 */
function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const signedInOnArrival = useRef<boolean | null>(null);
  if (loading) return <Splash />;
  if (signedInOnArrival.current === null) signedInOnArrival.current = user !== null;
  return signedInOnArrival.current ? <Navigate to="/" replace /> : <>{children}</>;
}

// Remount per recipe so the editor never shows the previous recipe's draft.
function EditorRoute() {
  const { id } = useParams();
  return <RecipeEditorPage key={id ?? "new"} />;
}

function RecipeRoute() {
  const { id } = useParams();
  return <RecipeDetailPage key={id} />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
      {/* Cooking mode is full screen: no navigation bars. */}
      <Route path="/cook/:id" element={<RequireAuth><CookPage /></RequireAuth>} />
      <Route element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route index element={<ExplorePage />} />
        <Route path="recipes/new" element={<EditorRoute />} />
        <Route path="recipes/:id" element={<RecipeRoute />} />
        <Route path="recipes/:id/edit" element={<EditorRoute />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="discover" element={<DiscoverStartPage />} />
        <Route path="discover/new" element={<DiscoverStartPage />} />
        <Route path="discover/:sessionId" element={<DeckPage />} />
        <Route path="discover/:sessionId/results" element={<DiscoverResultsPage />} />
        <Route path="tools/converter" element={<ConverterPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="profile/pantry" element={<PantryPage />} />
        <Route path="profile/kitchen" element={<KitchenPage />} />
        <Route path="profile/history" element={<HistoryPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

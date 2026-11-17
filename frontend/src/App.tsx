import { lazy, Suspense, useRef, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { AuthProvider, useAuth } from "./lib/auth";
import Landing from "./pages/Landing";
import { ForgotPassword, Login, Register, ResetPassword } from "./pages/Auth";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Detect = lazy(() => import("./pages/Detect"));
const DetectionReport = lazy(() => import("./pages/DetectionReport"));
const History = lazy(() => import("./pages/History"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Treatments = lazy(() => import("./pages/Treatments"));
const Chat = lazy(() => import("./pages/Chat"));
const Weather = lazy(() => import("./pages/Weather"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Profile = lazy(() => import("./pages/Profile"));
const Admin = lazy(() => import("./pages/Admin"));

function Protected({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/app" replace />;
  return <>{children}</>;
}

/** Redirects users who were already logged in when the page opened; lets the login/register
 * form itself navigate after a successful submit (avoids racing its own redirect). */
function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const wasLoggedIn = useRef<boolean | null>(null);
  if (loading) return <Spinner />;
  if (wasLoggedIn.current === null) wasLoggedIn.current = !!user;
  return wasLoggedIn.current ? <Navigate to="/app" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
            <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/app" element={<Protected><Layout /></Protected>}>
              <Route index element={<Dashboard />} />
              <Route path="detect" element={<Detect />} />
              <Route path="detections/:id" element={<DetectionReport />} />
              <Route path="history" element={<History />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="treatments" element={<Treatments />} />
              <Route path="treatments/:pest" element={<Treatments />} />
              <Route path="chat" element={<Chat />} />
              <Route path="weather" element={<Weather />} />
              <Route path="alerts" element={<Alerts />} />
              <Route path="profile" element={<Profile />} />
              <Route path="admin" element={<Protected admin><Admin /></Protected>} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

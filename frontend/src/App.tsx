import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import AlertsBell from "./components/AlertsBell";
import ChatPage from "./pages/ChatPage";
import OnboardingPage from "./pages/OnboardingPage";
import RoadmapPage from "./pages/RoadmapPage";
import SourcesPage from "./pages/SourcesPage";
import { isOnboarded } from "./profileOptions";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 font-bold ${isActive ? "bg-ink text-cream" : "text-ink hover:bg-cream-dark"}`;

// Checked when "/" mounts, not when App first renders: App renders once, so a check there
// would keep redirecting to /start even after onboarding saves and navigates home.
function Home() {
  return isOnboarded() ? <ChatPage /> : <Navigate to="/start" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-cream font-sans text-ink">
        <nav className="sticky top-0 z-30 border-b-2 border-ink bg-cream">
          <div className="mx-auto flex h-[4.5rem] max-w-6xl items-center gap-4 px-4 sm:px-6">
            <h1 className="text-2xl font-black tracking-tight sm:text-3xl">
              Path<span className="text-accent">finder</span>
            </h1>
            <div className="flex gap-1">
              <NavLink to="/" end className={linkClass}>
                Chat
              </NavLink>
              <NavLink to="/roadmap" className={linkClass}>
                Roadmaps
              </NavLink>
              <NavLink to="/sources" className={linkClass}>
                Sources
              </NavLink>
            </div>
            <div className="ml-auto">
              <AlertsBell />
            </div>
          </div>
        </nav>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/start" element={<OnboardingPage />} />
          <Route path="/roadmap" element={<RoadmapPage />} />
          <Route path="/sources" element={<SourcesPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

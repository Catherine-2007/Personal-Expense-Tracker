import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation, Link } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { useTheme } from "./ThemeContext";
import { useLanguage } from "./LanguageContext";
import { useCurrencyRates } from "./CurrencyRatesContext";
import Sidebar from "./components/Sidebar";
import HelpChatbot from "./components/HelpChatbot";
import OnboardingTour from "./components/OnboardingTour";
import AdultTransitionModal from "./components/AdultTransitionModal";
import SeniorTransitionModal from "./components/SeniorTransitionModal";
import ParticleField from "./components/ParticleField";
import ReceiptScanner from "./components/ReceiptScanner";
import Aurora from "./components/Aurora";
import ConfettiBurst from "./components/ConfettiBurst";
import { useGlobalFx } from "./hooks/useGlobalFx";
import { useMoney } from "./useMoney";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Expenses from "./pages/Expenses";
import Insights from "./pages/Insights";
import Interventions from "./pages/Interventions";
import Goals from "./pages/Goals";
import Report from "./pages/Report";
import Settings from "./pages/Settings";
import Budgets from "./pages/Budgets";
import Family from "./pages/Family";
import Guide from "./pages/Guide";
import Icon from "./components/Icon";
import CommandPalette from "./components/CommandPalette";

import { t } from "./i18n";

const AMBIENT_DENSITY = { kid: 45, teen: 28, adult: 16, senior: 10 };

function ProtectedLayout({ children }) {
  const { user } = useAuth();
  const { setTheme, setFontScale, setFontStyle, setLineSpacing } = useTheme();
  const { setLang } = useLanguage();
  const { rates, refresh: refreshRates } = useCurrencyRates();
  const [showTour, setShowTour] = useState(false);
  const [showAdultPrompt, setShowAdultPrompt] = useState(false);
  const [showSeniorPrompt, setShowSeniorPrompt] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const location = useLocation();
  const { money } = useMoney();
  const [confetti, setConfetti] = useState(false);
  useGlobalFx();
  useEffect(() => {
    const names = { "/": "Dashboard", "/expenses": "Expenses", "/goals": "Goals", "/budgets": "Budgets", "/insights": "Triggers & XAI", "/interventions": "Interventions", "/report": "Monthly Report", "/family": "Family", "/settings": "Settings", "/guide": "Feature guide" };
    document.title = `${names[location.pathname] ? t(names[location.pathname]) + " · " : ""}SpendSense-XAI`;
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen((o) => !o); }
    };
    const openPalette = () => setPaletteOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("ss:open-palette", openPalette);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("ss:open-palette", openPalette); };
  }, []);

  useEffect(() => {
    const open = () => setShowScanner(true);
    window.addEventListener("ss:open-scanner", open);
    return () => window.removeEventListener("ss:open-scanner", open);
  }, []);

  // Any page can listen for `ss:expense-added` to refresh its data.
  function handleSaved(exp) {
    window.dispatchEvent(new CustomEvent("ss:expense-added", { detail: exp }));
    setToast(exp);
    if (exp?.source === "scan") setConfetti(true);
    setTimeout(() => setToast(null), 4200);
  }

  // Apply the signed-in user's saved theme/language preference on load,
  // show a one-time welcome tour for brand-new sessions, and check
  // whether it's time to offer an age-based platform upgrade (18th
  // birthday -> Full, or 60th birthday -> Comfort).
  useEffect(() => {
    if (!user) return;
    if (user.theme) setTheme(user.theme);
    if (user.language) setLang(user.language);
    if (user.font_scale) setFontScale(user.font_scale);
    if (user.font_style) setFontStyle(user.font_style);
    if (user.line_spacing) setLineSpacing(user.line_spacing);

    // FX rates can't be fetched before login (the endpoint requires
    // auth), so make sure they're loaded now that we have a session.
    if (!rates) refreshRates();

    const seenKey = `ss_onboarded_${user.id}`;
    if (!localStorage.getItem(seenKey)) {
      setShowTour(true);
      localStorage.setItem(seenKey, "1");
    }

    if (user.should_prompt_adult_transition) {
      setShowAdultPrompt(true);
    } else if (user.should_prompt_senior_transition) {
      setShowSeniorPrompt(true);
    }
  }, [user]); // eslint-disable-line

  if (!user) return <Navigate to="/login" replace />;

  const ambientDensity = AMBIENT_DENSITY[user.platform_mode] ?? AMBIENT_DENSITY.adult;

  return (
    <div style={{ display: "flex", minHeight: "100vh", position: "relative" }}>
      {/* Ambient particle layer behind the whole app on every page — denser
          and more playful in kid mode, calmer in Comfort mode. Fixed so it
          doesn't scroll with content and sits behind everything. */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none" }}>
        <Aurora />
        <ParticleField density={ambientDensity} />
      </div>

      <div style={{ position: "relative", zIndex: 1, display: "flex", width: "100%" }}>
        <a href="#main" className="skip-link">{t("Skip to content")}</a>
        <Sidebar onScan={() => setShowScanner(true)} open={menuOpen} onClose={() => setMenuOpen(false)} />
        <div className="shell-col">
          <header className="topbar">
            <button className="icon-btn" onClick={() => setMenuOpen(true)} aria-label={t("Open menu")}><Icon name="menu" size={22} /></button>
            <div className="brand-name">SpendSense<span>{t("-XAI")}</span></div>
            <span style={{ display: "flex", gap: 2 }}>
              <button className="icon-btn" onClick={() => setPaletteOpen(true)} aria-label={t("Search or jump to…")}><Icon name="search" size={20} /></button>
              <button className="icon-btn" onClick={() => setShowScanner(true)} aria-label={t("Scan a bill")}><Icon name="scan" size={20} /></button>
            </span>
          </header>
        <main id="main" className="main-col">
          <ParentReturnBar />
          <div key={location.pathname} className="page-enter">{children}</div>
        </main>
        </div>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onScan={() => setShowScanner(true)} />
      {confetti && <ConfettiBurst onDone={() => setConfetti(false)} />}
      <HelpChatbot />
      {showScanner && (
        <ReceiptScanner mode={user.platform_mode} onClose={() => setShowScanner(false)} onSaved={handleSaved} />
      )}
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={16} />
          <span>{t("Added")} <b>{money(toast.amount)}</b> · {toast.merchant || t(toast.category)}</span>
          {location.pathname !== "/expenses" && <Link to="/expenses" onClick={() => setToast(null)}>{t("View")}</Link>}
        </div>
      )}
      {showAdultPrompt ? (
        <AdultTransitionModal onClose={() => setShowAdultPrompt(false)} />
      ) : showSeniorPrompt ? (
        <SeniorTransitionModal onClose={() => setShowSeniorPrompt(false)} />
      ) : (
        showTour && <OnboardingTour mode={user.platform_mode} onClose={() => setShowTour(false)} />
      )}
    </div>
  );
}

/** Shown while a parent is inside a child profile; one click returns to the parent's own account. */
function ParentReturnBar() {
  const { user } = useAuth();
  let parentToken = null;
  try { parentToken = localStorage.getItem("ss_parent_token"); } catch { /* ignore */ }
  if (!parentToken) return null;
  const back = () => {
    localStorage.setItem("ss_token", parentToken);
    localStorage.setItem("ss_user", localStorage.getItem("ss_parent_user") || "");
    localStorage.removeItem("ss_parent_token");
    localStorage.removeItem("ss_parent_user");
    window.location.assign("/family");
  };
  return (
    <div className="parent-bar" role="status">
      <span>{t("👀 You're viewing {name}'s profile", { name: user?.name })}</span>
      <button className="btn-ghost" onClick={back}>{t("← Back to my profile")}</button>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<ProtectedLayout><Dashboard /></ProtectedLayout>} />
      <Route path="/expenses" element={<ProtectedLayout><Expenses /></ProtectedLayout>} />
      <Route path="/insights" element={<ProtectedLayout><Insights /></ProtectedLayout>} />
      <Route path="/interventions" element={<ProtectedLayout><Interventions /></ProtectedLayout>} />
      <Route path="/goals" element={<ProtectedLayout><Goals /></ProtectedLayout>} />
      <Route path="/report" element={<ProtectedLayout><Report /></ProtectedLayout>} />
      <Route path="/budgets" element={<ProtectedLayout><Budgets /></ProtectedLayout>} />
      <Route path="/family" element={<ProtectedLayout><Family /></ProtectedLayout>} />
      <Route path="/guide" element={<ProtectedLayout><Guide /></ProtectedLayout>} />
      <Route path="/settings" element={<ProtectedLayout><Settings /></ProtectedLayout>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./theme.css";
import "./polish.css";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { AuthProvider } from "./AuthContext.jsx";
import { ThemeProvider } from "./ThemeContext.jsx";
import { LanguageProvider } from "./LanguageContext.jsx";
import { CurrencyRatesProvider } from "./CurrencyRatesContext.jsx";
import { FeedbackProvider } from "./FeedbackContext.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <LanguageProvider>
          <AuthProvider>
            <CurrencyRatesProvider>
              <FeedbackProvider><ErrorBoundary><App /></ErrorBoundary></FeedbackProvider>
            </CurrencyRatesProvider>
          </AuthProvider>
        </LanguageProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);

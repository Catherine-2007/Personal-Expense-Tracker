import { createContext, useContext, useState, useCallback, useMemo, useEffect, Fragment } from "react";
import { LANGUAGES, applyLanguage, loadCatalog, t, tp, tx, formatDate, formatDateTime, formatNumber } from "./i18n";

const LanguageContext = createContext(null);

const initialLang = () => {
  const saved = localStorage.getItem("ss_lang");
  return LANGUAGES.some((l) => l.id === saved) ? saved : "en";
};

/**
 * Holds the active language. Because the translation functions are plain
 * module functions (usable anywhere, even outside components), the whole
 * subtree is re-mounted when the language changes -- that guarantees every
 * piece of text on every page switches at once.
 */
export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  const [ready, setReady] = useState(false);

  // load the saved language before the first paint of the app
  useEffect(() => {
    let alive = true;
    loadCatalog(lang).then((cat) => {
      if (!alive) return;
      applyLanguage(lang, cat);
      document.documentElement.lang = lang;
      setReady(true);
    });
    return () => { alive = false; };
  }, []); // eslint-disable-line

  const setLang = useCallback(async (id) => {
    if (id === lang || !LANGUAGES.some((l) => l.id === id)) return;
    const cat = await loadCatalog(id);
    applyLanguage(id, cat);
    localStorage.setItem("ss_lang", id);
    document.documentElement.lang = id;
    setLangState(id);
  }, [lang]);

  const value = useMemo(
    () => ({ lang, setLang, t, tp, tx, formatDate, formatDateTime, formatNumber, languages: LANGUAGES.filter((l) => !l.hidden) }),
    [lang, setLang]
  );

  return (
    <LanguageContext.Provider value={value}>
      <Fragment key={lang}>{ready ? children : null}</Fragment>
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

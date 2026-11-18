/**
 * SpendSense-XAI internationalisation core.
 *
 * Text-as-key: the English sentence IS the key, so code stays readable:
 *     t("Add spending")                       -> translated, or English if missing
 *     t("You saved {amount}", { amount })     -> {placeholders} are filled in
 *     tp(n, "{n} day left", "{n} days left") -> simple singular/plural
 *     tx("Spent **{amount}** today", {...})   -> **bold** becomes <strong>
 *     N_("Food")                              -> marks a string for extraction
 *                                                without translating it yet
 *                                                (use t(value) where it is rendered)
 *
 * Translations live in src/locales/<lang>.json as { "English text": "Translation" }.
 * They are loaded on demand (one small file per language). Missing keys fall
 * back to English, so the UI never shows a blank or a raw key.
 *
 * Adding a language = add it to LANGUAGES, add a font, drop in locales/xx.json,
 * then run `npm run i18n:check`.
 */
import { createElement, Fragment } from "react";

// `locale` drives dates / numbers. "-u-nu-latn" (added below) keeps Latin
// digits so amounts look the same in every language.
export const LANGUAGES = [
  { id: "en", label: "English", locale: "en-IN" },
  { id: "hi", label: "हिन्दी", locale: "hi-IN" },
  { id: "ta", label: "தமிழ்", locale: "ta-IN" },
  { id: "te", label: "తెలుగు", locale: "te-IN" },
  { id: "bn", label: "বাংলা", locale: "bn-IN" },
  { id: "mr", label: "मराठी", locale: "mr-IN" },
  { id: "gu", label: "ગુજરાતી", locale: "gu-IN" },
  { id: "kn", label: "ಕನ್ನಡ", locale: "kn-IN" },
  { id: "ml", label: "മലയാളം", locale: "ml-IN" },
  { id: "pa", label: "ਪੰਜਾਬੀ", locale: "pa-IN" },
  { id: "es", label: "Español", locale: "es-ES" },
  { id: "fr", label: "Français", locale: "fr-FR" },
  { id: "zz", label: "Pseudo (dev)", locale: "en-IN", hidden: true }, // dev-only: see scripts/i18n-check.mjs --pseudo
];

// Older code used keys like "nav.dashboard"; they still work.
const LEGACY = {
  "nav.dashboard": "Dashboard",
  "nav.expenses": "Expenses",
  "nav.insights": "Triggers & XAI",
  "nav.interventions": "Interventions",
  "nav.goals": "Goals",
  "nav.report": "Monthly Report",
  "nav.settings": "Settings",
  "common.signOut": "Log out",
  "common.signIn": "Sign in",
  "common.add": "Add",
  "common.delete": "Delete",
  "common.save": "Save",
  "common.loading": "Loading…",
  "common.name": "Full name",
  "common.email": "Email",
  "common.password": "Password",
  "common.next": "Next",
  "common.back": "Back",
  "common.skip": "Skip tour",
  "common.finish": "Let's go!",
  "login.welcome": "Welcome back",
  "login.heading": "Sign in to SpendSense-XAI",
  "login.hint": "Demo account is pre-filled — just hit sign in.",
  "login.noAccount": "No account?",
  "login.createOne": "Create one",
  "register.heading": "Create your account",
  "register.age": "Your age",
  "register.ageHint": "We use this to set up an experience that fits you — younger users get a simpler, friendlier layout.",
  "register.currency": "Preferred currency",
  "register.language": "Preferred language",
  "register.income": "Monthly income (optional)",
  "register.savings": "Current savings (optional)",
  "register.guardian": "I have a parent or guardian's permission to use this app",
  "register.haveAccount": "Already have an account?",
  "dashboard.title": "Dashboard",
  "expenses.title": "Expenses",
  "insights.title": "Triggers & Explainable AI",
  "interventions.title": "Interventions",
  "goals.title": "Goals",
  "report.title": "Monthly Report",
  "settings.title": "Settings",
  "help.title": "Need help?",
  "help.placeholder": "Ask me anything about the app…",
  "onboarding.title": "Welcome to SpendSense-XAI!"
};

let currentLang = "en";
let catalog = {};

/** Called by LanguageProvider once a language file has been loaded. */
export function applyLanguage(lang, cat) {
  currentLang = lang;
  catalog = cat || {};
}
export const getLang = () => currentLang;
export const getLocale = () => LANGUAGES.find((l) => l.id === currentLang)?.locale || "en-IN";

const fill = (text, vars) =>
  vars ? text.replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined && vars[k] !== null ? String(vars[k]) : m)) : text;

export function t(text, vars) {
  if (typeof text !== "string") return text;
  const key = LEGACY[text] || text;
  return fill(catalog[key] || key, vars);
}

/** Marks a string for extraction; returns it unchanged. */
export const N_ = (text) => text;

/** Singular / plural by count; {n} is filled in automatically. */
export function tp(n, one, other, vars) {
  return t(Number(n) === 1 ? one : other, { n, ...vars });
}

/**
 * Like t(), but turns **bold** into <strong> and returns React nodes.
 * Use for sentences that highlight a value: tx("Spent **{amount}** today", { amount }).
 */
export function tx(text, vars) {
  const s = t(text, vars);
  const parts = s.split(/\*\*(.+?)\*\*/g);
  if (parts.length === 1) return s;
  return createElement(
    Fragment,
    null,
    parts.map((p, i) => (i % 2 ? createElement("strong", { key: i }, p) : p))
  );
}

/**
 * Like t(), but {placeholders} may be React nodes (e.g. a <b> or a component):
 *   tn("≈ {amount} a year", { amount: <b>{money(x)}</b> })
 */
export function tn(text, vars = {}) {
  const raw = (catalog[LEGACY[text] || text]) || LEGACY[text] || text;
  const parts = raw.split(/(\{\w+\})/g);
  return createElement(
    Fragment,
    null,
    parts.map((p, i) => {
      const m = /^\{(\w+)\}$/.exec(p);
      if (!m || vars[m[1]] === undefined) return p;
      const v = vars[m[1]];
      return typeof v === "object" && v !== null ? createElement(Fragment, { key: i }, v) : String(v);
    })
  );
}

/** "Late Night+Weekend" -> translated parts joined by `sep` (default " · "). */
export const contextLabel = (key, sep = " · ") =>
  String(key || "").split("+").map((p) => t(p)).join(sep);
// extraction markers for the dynamic context words
[N_("Late Night"), N_("Morning"), N_("Afternoon"), N_("Evening"), N_("Weekend"), N_("Weekday")];
// categories, payment methods and recurring cadences arrive from the API as English ids
[N_("Food"), N_("Groceries"), N_("Shopping"), N_("Transport"), N_("Bills"), N_("Entertainment"), N_("Health"), N_("Others"), N_("Other"),
 N_("UPI"), N_("Card"), N_("Cash"), N_("Wallet"), N_("Bank"),
 N_("weekly"), N_("monthly"), N_("quarterly"), N_("yearly"), N_("Weekly"), N_("Monthly"), N_("Quarterly"), N_("Yearly"), N_("Daily"), N_("Fortnightly")];

/* ---------- locale-aware formatting ---------- */
const loc = () => getLocale() + "-u-nu-latn";
export const formatDate = (d, opts = { day: "numeric", month: "short" }) =>
  new Intl.DateTimeFormat(loc(), opts).format(d instanceof Date ? d : new Date(d));
export const formatDateTime = (d, opts = { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) =>
  new Intl.DateTimeFormat(loc(), opts).format(d instanceof Date ? d : new Date(d));
export const formatNumber = (n, opts) => new Intl.NumberFormat(loc(), opts).format(n);

/* ---------- catalog loading (one JSON per language, on demand) ---------- */
const files = import.meta.glob(["./locales/*.json", "!./locales/_*.json"]);
export async function loadCatalog(lang) {
  if (lang === "en") return {};
  const loader = files[`./locales/${lang}.json`];
  if (!loader) return {};
  const mod = await loader();
  return mod.default || mod;
}

/** Strips leading emoji/pictographs from a (translated) label so it can sit next to a line icon. */
export function plain(label) {
  return String(label ?? "").replace(/^[\p{Extended_Pictographic}\uFE0F\u200D\s]+/u, "");
}

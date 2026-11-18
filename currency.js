import { N_ } from "./i18n";

export const CURRENCIES = [
  { code: "INR", label: N_("₹ Indian Rupee"), locale: "en-IN" },
  { code: "USD", label: N_("$ US Dollar"), locale: "en-US" },
  { code: "EUR", label: N_("€ Euro"), locale: "de-DE" },
  { code: "GBP", label: N_("£ British Pound"), locale: "en-GB" },
  { code: "JPY", label: N_("¥ Japanese Yen"), locale: "ja-JP" },
  { code: "AUD", label: N_("A$ Australian Dollar"), locale: "en-AU" },
  { code: "CAD", label: N_("C$ Canadian Dollar"), locale: "en-CA" },
  { code: "SGD", label: N_("S$ Singapore Dollar"), locale: "en-SG" },
  { code: "AED", label: N_("د.إ UAE Dirham"), locale: "ar-AE" },
];

/**
 * Formats a raw numeric amount using the given currency code's symbol and
 * grouping conventions. This is DISPLAY formatting only — amounts are
 * stored as plain numbers, so switching currency changes how a number is
 * shown, not what it's worth. Real conversion would need a live FX-rate
 * source, which is intentionally out of scope for this project.
 */
export function formatCurrency(amount, currencyCode = "INR") {
  const meta = CURRENCIES.find((c) => c.code === currencyCode) || CURRENCIES[0];
  try {
    return new Intl.NumberFormat(meta.locale + "-u-nu-latn", {
      style: "currency",
      currency: meta.code,
      maximumFractionDigits: meta.code === "JPY" ? 0 : 2,
    }).format(amount || 0);
  } catch {
    return `${meta.code} ${Number(amount || 0).toLocaleString()}`;
  }
}

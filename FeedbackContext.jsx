import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import Icon from "./components/Icon";
import { t } from "./i18n";

/**
 * App-wide feedback: a styled confirm dialog (replaces window.confirm) and
 * toast messages. Usage:
 *   const { confirm, notify } = useFeedback();
 *   if (await confirm({ message: t("Delete this goal?"), danger: true })) ...
 *   notify(t("Saved"));           notify(t("Failed"), "error");
 */
const Ctx = createContext({ confirm: async () => true, notify: () => {} });
export const useFeedback = () => useContext(Ctx);

export function FeedbackProvider({ children }) {
  const [dlg, setDlg] = useState(null);
  const [toasts, setToasts] = useState([]);
  const okRef = useRef(null);

  const confirm = useCallback((opts) => new Promise((resolve) => setDlg({ ...opts, resolve })), []);
  const close = (val) => { dlg?.resolve(val); setDlg(null); };

  const notify = useCallback((message, kind = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((x) => [...x.slice(-2), { id, message, kind }]);
    setTimeout(() => setToasts((x) => x.filter((i) => i.id !== id)), 3800);
  }, []);

  useEffect(() => {
    if (!dlg) return undefined;
    const onKey = (e) => { if (e.key === "Escape") close(false); };
    window.addEventListener("keydown", onKey);
    okRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }); // eslint-disable-line

  return (
    <Ctx.Provider value={{ confirm, notify }}>
      {children}
      {dlg && (
        <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && close(false)}>
          <div className="confirm-dialog card" role="alertdialog" aria-modal="true" aria-labelledby="cf-title" aria-describedby="cf-msg">
            <div className={`confirm-ico ${dlg.danger ? "danger" : ""}`}><Icon name={dlg.danger ? "alert" : "info"} size={22} /></div>
            <h3 id="cf-title">{dlg.title || (dlg.danger ? t("Are you sure?") : t("Please confirm"))}</h3>
            <p id="cf-msg">{dlg.message}</p>
            <div className="confirm-actions">
              <button className="btn-ghost" onClick={() => close(false)}>{dlg.cancelLabel || t("Cancel")}</button>
              <button ref={okRef} className={dlg.danger ? "btn-danger-solid" : "btn-primary"} onClick={() => close(true)}>
                {dlg.confirmLabel || (dlg.danger ? t("Delete") : t("Confirm"))}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="snack-stack" aria-live="polite">
        {toasts.map((x) => (
          <div key={x.id} className={`snack ${x.kind}`} role="status">
            <Icon name={x.kind === "error" ? "alert" : "check"} size={16} />
            <span>{x.message}</span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

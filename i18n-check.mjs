// Validates translation catalogs against the strings found in src/.
//   node scripts/i18n-check.mjs            -> report missing / broken translations (exit 1 on problems)
//   node scripts/i18n-check.mjs --pseudo   -> write locales/zz.json ("⟦text⟧") for hunting untranslated UI
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), "../src/locales");
const keys = JSON.parse(fs.readFileSync(path.join(dir, "_keys.json"), "utf8"));
const ph = (s) => (String(s).match(/\{\w+\}/g) || []).sort().join(",");

if (process.argv.includes("--pseudo")) {
  const o = {};
  for (const k of keys) o[k] = k.startsWith("kw:") ? "zzpseudo" : "⟦" + k + "⟧";
  fs.writeFileSync(path.join(dir, "zz.json"), JSON.stringify(o, null, 1));
  console.log("wrote zz.json (" + keys.length + " keys)");
  process.exit(0);
}
let bad = 0;
for (const f of fs.readdirSync(dir).filter((f) => /^[a-z]{2}\.json$/.test(f) && f !== "zz.json")) {
  const cat = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
  const missing = keys.filter((k) => !cat[k]);
  const broken = keys.filter((k) => cat[k] && !k.startsWith("kw:") && ph(cat[k]) !== ph(k));
  const stale = Object.keys(cat).filter((k) => !keys.includes(k));
  console.log(`${f.padEnd(9)} ${keys.length - missing.length}/${keys.length} translated` +
    (broken.length ? `  ${broken.length} placeholder mismatches` : "") + (stale.length ? `  ${stale.length} unused` : ""));
  broken.slice(0, 5).forEach((k) => console.log("   ✗", k, "=>", cat[k]));
  missing.slice(0, 5).forEach((k) => console.log("   ? missing:", k));
  bad += missing.length + broken.length;
}
process.exit(bad ? 1 : 0);

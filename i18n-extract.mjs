// Collects every translatable string used in src/ -> src/locales/_keys.json
// Usage: node scripts/i18n-extract.mjs   (npm run i18n:extract)
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "@babel/parser";
import traverseMod from "@babel/traverse";
const traverse = traverseMod.default || traverseMod;
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "../src");
const files = [];
(function walk(d) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) { if (f !== "locales") walk(p); }
    else if (/\.jsx?$/.test(f)) files.push(p);
  }
})(root);

const keys = new Map(); // text -> first place
const add = (text, where) => {
  if (typeof text !== "string" || !text.trim()) return;
  if (/^[\w]+(\.[\w]+)+$/.test(text)) return; // legacy dotted ids
  if (!keys.has(text)) keys.set(text, where);
};
const str = (n) => n && (n.type === "StringLiteral" ? n.value
  : n.type === "TemplateLiteral" && n.expressions.length === 0 ? n.quasis[0].value.cooked : null);

for (const f of files) {
  const ast = parse(fs.readFileSync(f, "utf8"), { sourceType: "module", plugins: ["jsx"] });
  traverse(ast, {
    CallExpression({ node }) {
      const c = node.callee;
      const name = c.type === "Identifier" ? c.name : c.type === "MemberExpression" ? c.property.name : "";
      const where = path.relative(root, f) + ":" + (node.loc?.start.line || 0);
      if (["t", "tx", "tn", "N_"].includes(name)) add(str(node.arguments[0]), where);
      else if (name === "tp") { add(str(node.arguments[1]), where); add(str(node.arguments[2]), where); }
    },
  });
}
// older code uses ids like "nav.dashboard"; their English text lives in LEGACY (i18n.js)
const legacy = fs.readFileSync(path.join(root, "i18n.js"), "utf8").match(/const LEGACY = \{([\s\S]*?)\n\};/);
if (legacy) for (const m of legacy[1].matchAll(/:\s*("(?:[^"\\]|\\.)*")/g)) add(JSON.parse(m[1]), "i18n.js");
// strings produced by the API (python side) are shown through t() in the UI too
const be = path.join(root, "../../backend/app/locales/_keys.json");
if (fs.existsSync(be)) for (const k of JSON.parse(fs.readFileSync(be, "utf8"))) add(k, "backend");
const out = [...keys.keys()].sort();
fs.mkdirSync(path.join(root, "locales"), { recursive: true });
fs.writeFileSync(path.join(root, "locales/_keys.json"), JSON.stringify(out, null, 1));
console.log(`${out.length} strings -> src/locales/_keys.json`);

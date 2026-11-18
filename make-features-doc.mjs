// Writes docs/FEATURES.md from src/guideContent.js (same text as the in-app Feature guide).
//   node scripts/make-features-doc.mjs
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const here = path.dirname(fileURLToPath(import.meta.url));
let src = fs.readFileSync(path.join(here, "../src/guideContent.js"), "utf8")
  .replace(/^import .*$/m, "const N_ = (s) => s;")
  .replace(/export const /g, "const ");
const { GUIDE, GUIDE_LOOP } = new Function(src + "\nreturn { GUIDE, GUIDE_LOOP };")();

const routeName = { "/": "Dashboard", "/expenses": "Expenses", "/goals": "Goals", "/budgets": "Budgets", "/insights": "Triggers & XAI",
  "/interventions": "Interventions", "/report": "Monthly Report", "/family": "Family", "/settings": "Settings", "/guide": "Feature guide" };
let md = `# SpendSense-XAI - Feature guide

*Written for staff and reviewers. The same text is available inside the app under **Feature guide** (sidebar).*

## The idea in one line

Most expense trackers only record. SpendSense-XAI **learns your habits, explains them with proof, suggests one small change, and measures whether it worked.**

${GUIDE_LOOP.map((s, i) => `${i + 1}. **${s.k}** - ${s.d}`).join("\n")}

## Quick start for a reviewer (5 minutes)

1. Sign in with \`demo@spendsense.app\` / \`demo1234\` (history already loaded).
2. **Dashboard** - read *Safe to spend today*, the subscription radar and the heatmap.
3. **Expenses** - type \`450 swiggy dinner upi yesterday\` into *Magic add*, then press **Scan a bill** and drop in any receipt photo.
4. **Triggers & XAI** - open a trigger card to see the evidence behind it.
5. **Goals** - press **Add money** on a goal.  **Budgets** - set a limit and add an expense that crosses it.
6. **Family** - join with code \`DEMO42\` to see the leaderboard and challenges.
7. **Settings** - try another language, bigger text, a different theme and age mode.

Demo accounts (password \`demo1234\` for all): \`demo@spendsense.app\` (adult), \`teen@spendsense.app\`, \`kid@spendsense.app\`, \`senior@spendsense.app\`.

---
`;
for (const s of GUIDE) {
  md += `\n## ${s.title}\n\n*${s.blurb}*\n\n`;
  for (const i of s.items) {
    md += `### ${i.name}\n\n- **What it does:** ${i.what}\n- **How it works:** ${i.how}\n` + (i.to ? `- **Where:** ${routeName[i.to] || i.to} page\n` : "") + "\n";
  }
}
md += `---\n\n## Where the data lives\n\nSee [\`database/README.md\`](../database/README.md) for SQLite vs MySQL/MariaDB (XAMPP, phpMyAdmin), the table list and troubleshooting.\n`;
fs.mkdirSync(path.join(here, "../../docs"), { recursive: true });
fs.writeFileSync(path.join(here, "../../docs/FEATURES.md"), md);
console.log("docs/FEATURES.md written,", md.split("\n").length, "lines");

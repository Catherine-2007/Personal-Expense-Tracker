# SpendSense-XAI - Feature guide

*Written for staff and reviewers. The same text is available inside the app under **Feature guide** (sidebar).*

## The idea in one line

Most expense trackers only record. SpendSense-XAI **learns your habits, explains them with proof, suggests one small change, and measures whether it worked.**

1. **Detect** - Finds habits in your own spending
2. **Explain** - Shows the proof behind every claim
3. **Nudge** - Suggests one small change
4. **Measure** - Checks if the change really worked
5. **Learn** - Keeps what works, drops what doesn't

## Quick start for a reviewer (5 minutes)

1. Sign in with `demo@spendsense.app` / `demo1234` (history already loaded).
2. **Dashboard** - read *Safe to spend today*, the subscription radar and the heatmap.
3. **Expenses** - type `450 swiggy dinner upi yesterday` into *Magic add*, then press **Scan a bill** and drop in any receipt photo.
4. **Triggers & XAI** - open a trigger card to see the evidence behind it.
5. **Goals** - press **Add money** on a goal.  **Budgets** - set a limit and add an expense that crosses it.
6. **Family** - join with code `DEMO42` to see the leaderboard and challenges.
7. **Settings** - try another language, bigger text, a different theme and age mode.

Demo accounts (password `demo1234` for all): `demo@spendsense.app` (adult), `teen@spendsense.app`, `kid@spendsense.app`, `senior@spendsense.app`.

---

## Record your spending

*Several ways to log an expense - pick whichever is fastest for you.*

### Add an expense

- **What it does:** Type amount, shop, payment method and an optional note. Category and date are picked for you but you can change both.
- **How it works:** The category is guessed from the shop name and note using keyword rules, and you can always override it. Amounts you type in your display currency are converted to your account currency automatically.
- **Where:** Expenses page

### Scan a bill (camera or photo)

- **What it does:** Take a photo of a bill, upload one, or paste e-receipt text. The shop, total, date, payment method and category are filled in for you to confirm.
- **How it works:** Text is read on your own device (nothing is uploaded as an image). The picture is first straightened and cleaned, then a parser picks the real total (ignoring subtotal, tax and change), repairs common reading mistakes like 2B0 for 280, and cross-checks the line items. If it is unsure it offers other likely totals.
- **Where:** Expenses page

### Magic add (type or speak)

- **What it does:** Write one sentence such as '450 swiggy dinner upi yesterday' and the whole form is filled in.
- **How it works:** A language parser pulls out the amount, shop, payment method and relative date. The microphone button uses your browser's speech recognition in your chosen language.
- **Where:** Expenses page

### Search, filter, edit and delete

- **What it does:** Find any past expense by shop or note, filter by category or dates, fix mistakes or remove entries.
- **How it works:** Filters run on the database, and the running total always matches what you see in the list.
- **Where:** Expenses page

### Import and export (CSV)

- **What it does:** Bring your old data in from a spreadsheet, or download everything to keep a backup.
- **How it works:** Import understands many column names and date formats and skips duplicates. Export is safe to open in Excel.
- **Where:** Settings page


## Plan and save

*Set targets, then see early if you are drifting from them.*

### Savings goals

- **What it does:** Create goals such as 'Buy Laptop', add or take out money, see the full history and celebrate when you hit 100%.
- **How it works:** Every deposit and withdrawal is stored as its own record, so the history always adds up. You cannot take out more than the goal holds.
- **Where:** Goals page

### Monthly budgets

- **What it does:** Set one overall limit and/or a limit per category. Bars turn amber at 80% and red at 100%.
- **How it works:** This month's spending is compared to each limit, and the pace so far is projected to month end to warn you before you overspend. A warning also appears right after you log an expense that crosses a limit.
- **Where:** Budgets page

### Safe to spend today

- **What it does:** One number: how much you can spend today and still stay on track.
- **How it works:** Your income (or your own average), minus what your goals need this month, minus what you already spent, divided by the days left.
- **Where:** Dashboard page

### 14-day forecast

- **What it does:** A line showing where your spending is heading, including bills that are about to fall due.
- **How it works:** Uses your own weekday habits plus detected recurring bills, then tells you if you will finish the month on track, tight or over.
- **Where:** Dashboard page

### Spare-change jar

- **What it does:** Shows how much you would have saved if every purchase were rounded up to the next 5, 10, 50 or 100.
- **How it works:** Pure arithmetic on your real purchases, with a yearly projection.
- **Where:** Dashboard page


## Understand your habits

*This is what makes SpendSense-XAI different: it explains itself.*

### Spending triggers

- **What it does:** Finds repeating situations behind your spending, for example 'late-night food orders on weekdays'.
- **How it works:** Groups expenses by time of day, day type and payment method, then scores each pattern with a confidence value. Recent behaviour counts more than old behaviour, and habits you stop fade away.
- **Where:** Triggers & XAI page

### Explainable AI (XAI)

- **What it does:** Click any trigger to see exactly why it was flagged.
- **How it works:** Every statement shows the counted evidence behind it (how many times, how much, since when). Nothing is a black box.
- **Where:** Triggers & XAI page

### Interventions (nudges)

- **What it does:** Small suggestions such as 'wait 20 minutes before ordering', with a real before-and-after result.
- **How it works:** Two different nudge styles are tried against each other. After a few days your actual spending before and after is compared, and the better style is kept. A thumbs-down removes a nudge immediately.
- **Where:** Interventions page

### Monthly report

- **What it does:** The big picture: this month versus your own past, what changed and why, and whether your goals are on pace.
- **How it works:** You are only ever compared to your own last three months, never to other people. A what-if simulator shows the yearly saving of a small habit change.
- **Where:** Monthly Report page

### Subscription radar

- **What it does:** Lists everything that repeats (Netflix, gym, electricity), when it is next due and what it costs per year.
- **How it works:** Looks for same-shop charges at regular gaps, and warns when a price quietly goes up.
- **Where:** Dashboard page

### Unusual-spend guard

- **What it does:** Warns when a purchase is far bigger than your normal for that category.
- **How it works:** Uses robust statistics (median based, so one big purchase does not distort it) and needs at least five similar past purchases.
- **Where:** Dashboard page

### Spending heatmap and persona

- **What it does:** A calendar of busy and quiet days, plus a friendly spending personality such as 'Night Owl Nibbler'.
- **How it works:** Day colours are based on quantiles of your own days. The persona comes from your last 90 days, with the numbers that earned it.
- **Where:** Dashboard page


## Family space

*One app for the whole household, with privacy for each person.*

### Create or join a family

- **What it does:** Make a family, share the invite code, or add a child profile yourself.
- **How it works:** Roles are owner, parent, member and child. Each person has their own login and their own private data.
- **Where:** Family page

### Who spends what

- **What it does:** See each member's spending for the week or month side by side.
- **How it works:** Each person chooses what others can see: everything, totals only, or rank only. The app always respects that choice.
- **Where:** Family page

### Healthy-habit leaderboard

- **What it does:** A podium that rewards good habits, not low spending.
- **How it works:** Points come from logging days, streaks, no-spend days, beating your own usual pace and goal progress, so nobody wins just by spending less or more than others.
- **Where:** Family page

### Challenges, awards and kudos

- **What it does:** Family challenges such as a no-spend day, awards like Streak Master, and cheers you can send each other.
- **How it works:** Progress is calculated from real expenses. Cheers are limited per day to keep them meaningful.
- **Where:** Family page


## Made for everyone

*The same app adapts to age, eyesight, language and taste.*

### Four age experiences

- **What it does:** Playground (kids), Guided (teens), Full (adults) and Comfort (seniors) change wording, layout and rewards.
- **How it works:** Your date of birth suggests a mode, and the app offers to upgrade you at 18 and 60. You can switch any time.
- **Where:** Settings page

### 12 languages

- **What it does:** English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Spanish and French.
- **How it works:** Every screen, message and insight switches together. Dates and numbers follow the language.
- **Where:** Settings page

### Text size and font style

- **What it does:** Make text bigger, choose a font (including dyslexia-friendly and low-vision fonts) and loosen line spacing.
- **How it works:** Saved to your account, so it follows you to every device.
- **Where:** Settings page

### Themes and visual effects

- **What it does:** Five themes, plus effects you can turn to Full, Subtle or Off.
- **How it works:** Effects switch off automatically if your device asks for reduced motion.
- **Where:** Settings page

### Currencies

- **What it does:** Nine currencies with correct formatting.
- **How it works:** Amounts are stored in your account currency and converted with live exchange rates when you view them in another one, with an offline fallback table.
- **Where:** Settings page

### Quick search (Ctrl K)

- **What it does:** Press Ctrl + K (or Cmd + K on a Mac), or tap the search button, to jump to any page or start an action without using the menu.
- **How it works:** Type a few letters, use the arrow keys and press Enter. It only lists pages and actions, so it works instantly and sends nothing anywhere.

### Help chat

- **What it does:** The chat bubble answers 'how do I...' questions about the app.
- **How it works:** It is rule-based and runs on your own server, so nothing is sent to an outside service.


## Your data and security

*Where your information lives and who can see it.*

### Database (SQLite or MySQL)

- **What it does:** All records live in one database. It starts with a simple file (SQLite) and can switch to MySQL/MariaDB (XAMPP) so you can see every table in phpMyAdmin.
- **How it works:** Tables are created and upgraded automatically on start-up. The Settings page shows a health light and which database is in use. For phpMyAdmin, import database/spendsense_mysql.sql (never the .db file), or run python setup_mysql.py to do everything in one step.

### Sign-in and passwords

- **What it does:** Passwords are stored as one-way hashes. You can change your password or delete your account and all its data at any time.
- **How it works:** Logins use signed, expiring tokens, and repeated attempts are rate limited.
- **Where:** Settings page

### Privacy by design

- **What it does:** Bill photos are read on your device, comparisons are only against yourself, and family sharing is opt-in per person.
- **How it works:** No bill image is ever sent to a server, and no data is sold or shared.

---

## Where the data lives

See [`database/README.md`](../database/README.md) for SQLite vs MySQL/MariaDB (XAMPP, phpMyAdmin), the table list and troubleshooting.

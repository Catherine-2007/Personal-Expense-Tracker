"""
In-app Help Assistant.

A transparent, rule-based FAQ matcher (no external AI API calls, no data
leaves your machine) that answers "how do I..." and "what does this
mean..." questions about SpendSense-XAI itself. Every entry is hand-written
so answers stay accurate.

Multilingual: answers are looked up with tr() so they come back in the
caller's language. To let people *ask* in their own language, each entry also
has a translated keyword list in the language catalog under the key
"kw:<first English keyword>" (keywords separated by "|"). English keywords
always keep working in every language.

Matching: weighted keywords (longer phrases score higher), word-boundary
matching on lightly stemmed tokens, and a kid-friendly variant per entry.
Extending this is just appending to FAQ_ENTRIES.
"""
from __future__ import annotations
import re
from typing import List, Tuple, Optional, Dict

from ..i18n import N_, tr

Entry = Dict[str, object]  # {"keywords": [...], "default": str, "kid": Optional[str]}

FAQ_ENTRIES: List[Entry] = [
    {
        "keywords": ["add expense", "log expense", "new expense", "record spending", "spend", "log"],
        "default": N_("Go to the **Expenses** page, fill in the amount and where you spent it, then hit **Add**. The app guesses the category for you automatically."),
        "kid": N_("Tap **Add Spending**, type in what you bought and how much it cost, then hit **Add**. The app figures out the category for you — like magic! 🪄"),
    },
    {
        "keywords": ["fix category", "wrong category", "change category", "recategorize", "miscategorized"],
        "default": N_("There's no manual override yet in this version — categories are auto-detected from the merchant name and note you enter. Try including the store name (e.g. 'Swiggy', 'Uber') for a more accurate guess."),
    },
    {
        "keywords": ["what is a trigger", "trigger", "pattern", "spending pattern", "habit detected"],
        "default": N_("A **trigger** is a spending habit the app noticed, like 'you tend to order food late at night.' Go to **Triggers & XAI** and click a card to see the exact evidence behind it."),
        "kid": N_("A **pattern** is something the app noticed about your spending, like 'you buy snacks after school a lot!' Tap **My Patterns** to see what it found and why."),
    },
    {
        "keywords": ["no triggers", "trigger not showing", "not finding patterns", "empty triggers"],
        "default": N_("The trigger engine needs at least a few similar expenses in a shared context (like 3+ late-night orders) before it's confident enough to call something a pattern. Log a few more expenses, then click **Refresh triggers** again."),
    },
    {
        "keywords": ["confidence", "percentage ring", "confidence score", "how sure"],
        "default": N_("The percentage ring shows how confident the app is about a pattern, based on how consistently it happened in your own history. Higher % means it happened more often in that context."),
        "kid": N_("The circle with a number shows how sure the app is about a pattern. A bigger number means it happened a LOT."),
    },
    {
        "keywords": ["intervention", "nudge", "suggestion", "habit change", "get a tip"],
        "default": N_("An **intervention** is a small suggestion to help with a habit — like 'wait 24 hours before buying' or 'set a budget cap.' Find them on the **Interventions** page after clicking 'Suggest an intervention' on a trigger."),
        "kid": N_("The app can give you a little **tip** to help with a habit, like waiting a day before buying something. Find your tips on the **Fun Tips** page!"),
    },
    {
        "keywords": ["a/b test", "ab test", "variant", "which nudge works", "two versions"],
        "default": N_("The app tries two different kinds of nudges across your triggers (that's the A/B test) and tracks which one actually reduces your spending over time."),
    },
    {
        "keywords": ["measure result", "did it work", "effectiveness", "measure intervention"],
        "default": N_("Click **Measure result** on an intervention to compare your spending before and after the nudge. A negative percentage means you spent less — that's the goal."),
        "kid": N_("Tap **Measure result** to see if your tip is helping you spend less. If the number is lower, you're doing great!"),
    },
    {
        "keywords": ["thumbs down", "thumbs up", "feedback", "intervention not working", "stop nudge"],
        "default": N_("Use the 👍/👎 buttons on any intervention. A 👎 immediately retires that nudge so you won't be shown it again in that form."),
    },
    {
        "keywords": ["counterfactual", "what if simulator", "simulate savings", "what if i"],
        "default": N_("The **counterfactual simulator** on the Insights page lets you drag a slider to see how much you'd save if you cut a habit by a few times a week, based on your own average transaction size."),
        "kid": N_("There's a fun slider on the **My Patterns** page that shows how much you could save if you buy something a little less often!"),
    },
    {
        "keywords": ["goal", "save for", "savings target", "add a goal", "piggy bank"],
        "default": N_("Add a savings goal (like 'New Bike' or 'Buy Laptop') on the **Goals** page. The Monthly Report will tell you if your current spending pace is on track to reach it."),
        "kid": N_("Tap **My Piggy Bank** and tell the app what you're saving up for. Watch your piggy bank fill up as you save! 🐷"),
    },
    {
        "keywords": ["monthly report", "report page", "summary", "how am i doing"],
        "default": N_("The **Monthly Report** page shows your total spend, how it compares to your own past months, what changed, and whether your goals are on track."),
        "kid": N_("**My Story** shows how your money went this month, and whether you're saving enough for your piggy bank goal!"),
    },
    {
        "keywords": ["habit score", "financial score", "what does my score mean", "score out of"],
        "default": N_("The **Financial Habit Score** (0–100) is a summary of how your month is going — it rises when your spending trends down and your goals stay on track."),
        "kid": N_("Your **star score** (out of 5 stars ⭐) shows how well you're doing with your money this month. More stars is better!"),
    },
    {
        "keywords": ["streak", "logging streak", "days in a row"],
        "default": N_("Your **streak** counts consecutive days you've logged at least one expense. It resets if you go more than a day without logging anything."),
        "kid": N_("Your **streak** counts the days in a row you've added your spending. Keep it going to unlock more badges! 🔥"),
    },
    {
        "keywords": ["badge", "badges", "unlock", "earn a badge", "achievement"],
        "default": N_("Badges are earned automatically from real activity — your first expense, a 3-day streak, discovering a trigger, setting a goal, and more. Check the Dashboard to see which ones you've earned."),
        "kid": N_("Badges are little rewards for using the app — like logging spending 3 days in a row! Check your Dashboard to see your badges. 🏆"),
    },
    {
        "keywords": ["currency", "rupee", "dollar", "change money symbol", "convert currency"],
        "default": N_("You can change your display currency in **Settings**. Your entries are recorded in the currency you signed up with, and switching the display currency converts every amount using a real, live exchange rate — not just the symbol. If the app can't reach the internet, it falls back to a recent saved rate and tells you so."),
    },
    {
        "keywords": ["language", "hindi", "spanish", "french", "tamil", "telugu", "bengali", "marathi", "gujarati", "kannada", "malayalam", "punjabi", "translate", "change language"],
        "default": N_("You can switch the app's language from **Settings** (or the language picker on the sign-in page). Every page, tip, report and help answer is translated. Currently supported: English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Spanish and French."),
    },
    {
        "keywords": ["theme", "dark mode", "light mode", "color scheme", "playground theme", "ocean theme", "font", "font size", "text size", "bigger text", "font style", "dyslexia"],
        "default": N_("Click the theme switcher at the top of the sidebar (or go to Settings) to pick between Night, Daylight, Deep Ocean, Playground or Comfort. In **Settings → Text & reading** you can also change the font size, font style (including a dyslexia-friendly one) and line spacing."),
    },
    {
        "keywords": ["platform mode", "kid mode", "teen mode", "adult mode", "experience level"],
        "default": N_("Your **platform mode** (Playground / Guided / Full) controls how much simplification and guidance the app shows. It's suggested from your age at signup but you can change it any time in Settings."),
    },
    {
        "keywords": ["turn 18", "birthday", "adult transition", "turned eighteen"],
        "default": N_("If your account is set to a Playground or Guided experience and your date of birth shows you're now 18+, the app offers a one-time prompt to switch to the Full experience. You can say 'not now' and it won't ask again, or switch any time yourself in Settings."),
    },
    {
        "keywords": ["guardian", "parent permission", "child account", "under 13"],
        "default": N_("Accounts for users under 13 show a checkbox at signup confirming a parent or guardian is aware of the account. A parent or guardian should still be the one setting up and overseeing use for a young child."),
    },
    {
        "keywords": ["password", "forgot password", "reset password", "can't log in", "cant log in"],
        "default": N_("There's no password-reset flow in this demo yet — if you forget your password, you'll need to register a new account for now."),
    },
    {
        "keywords": ["safe", "secure", "privacy", "is my data private", "who sees my data"],
        "default": N_("Your password is hashed (never stored in plain text), and your financial data is only ever compared against your *own* history — never shared with or compared to other users."),
        "kid": N_("Your info is kept safe, and the app never compares your money to other kids' money — it only looks at your own!"),
    },
    {
        "keywords": ["delete expense", "remove expense", "undo", "delete goal"],
        "default": N_("Click the **Delete** button next to any expense or goal to remove it."),
    },
    {
        "keywords": ["income", "monthly income", "how much do i make"],
        "default": N_("Your monthly income is used by the Goal-Conflict Detector to estimate your savings rate. Set or update it any time from **Settings**."),
    },
    {
        "keywords": ["export data", "download my data", "backup", "csv", "export"],
        "default": N_("Go to **Settings → Export & connection** and click **Download all expenses (CSV)** to get your data in a spreadsheet-friendly file."),
    },
    {
        "keywords": ["xampp", "mysql", "database setup", "phpmyadmin"],
        "default": N_("By default the app uses a simple built-in database (SQLite). If you want to use XAMPP/MySQL instead, check the README's 'Using XAMPP / MySQL' section for the exact steps — it walks through creating the database and pointing the app at it."),
    },
    {
        "keywords": ["who are you", "are you ai", "chatbot", "are you real ai", "what are you"],
        "default": N_("I'm a simple, rule-based helper built into this app — I match your question against a list of topics I know about. I'm not a general AI model, I don't learn from conversations, and nothing you type here leaves your own app."),
        "kid": N_("I'm a helper robot built right into the app! I can answer questions about how to use SpendSense-XAI. 🤖"),
    },
    {
        "keywords": ["financial advice", "should i buy", "is this legal advice", "invest"],
        "default": N_("I can explain how this app's features work, but I can't give personal financial advice — for real decisions about spending, saving, or investing, it's best to talk to a trusted adult, a financial advisor, or do your own research."),
    },
    {
        "keywords": ["mobile", "phone", "app store", "install app", "ios", "android"],
        "default": N_("This is a web app — open it in your phone's browser at the same address, and it'll resize to fit your screen. There's no separate app-store download in this version."),
    },
    {
        "keywords": ["scan bill", "scan receipt", "photo upload", "upload bill", "camera", "ocr", "receipt", "bill photo"],
        "default": N_("Tap **Scan a bill** in the sidebar, then take a photo, upload one or paste the bill's text. The app reads the merchant, date and total on your own device (nothing is uploaded) and fills in the expense. Check any amber fields, then save."),
        "kid": N_("Tap **Snap a receipt**, take a picture of the bill and the app fills in your spending for you! 📸"),
    },
    {
        "keywords": ["safe to spend", "daily allowance", "how much can i spend today", "allowance"],
        "default": N_("**Safe to spend** shows how much you can spend today without hurting your goals. It is your monthly budget, minus what you've already spent and what you've set aside for goals, spread over the days left."),
    },
    {
        "keywords": ["family", "family group", "household", "invite code", "join family", "add family member", "family member"],
        "default": N_("Open **Family** in the sidebar to create a family group or join one with an invite code. Everybody keeps their own account and sees their own spending; the family page adds shared totals, a friendly leaderboard, challenges and badges. Each member chooses how much of their spending others can see."),
        "kid": N_("Open **Family** to join your family team with a secret code! You can see who's saving the most and win badges together. 👨‍👩‍👧"),
    },
    {
        "keywords": ["leaderboard", "ranking", "rank", "who spends least", "winner", "champion", "family challenge", "challenge"],
        "default": N_("The **Family leaderboard** ranks members on healthy habits — saving, logging streaks and staying under budget — not on who spends the most or least. Challenges give the whole family a shared goal to work on together."),
        "kid": N_("The leaderboard shows who has the best money habits this week. Everyone can win different badges, so it's all about having fun! 🏆"),
    },
    {
        "keywords": ["family privacy", "hide my spending", "who can see my spending", "private spending", "privacy level"],
        "default": N_("In **Family → My sharing** you choose what the family sees: everything, only totals, or just your ranking points. Parents of children under 13 can always see their child's activity."),
    },
]

GREETINGS = ["hi", "hello", "hey", "yo", "sup", "hiya"]
THANKS = ["thanks", "thank you", "thx", "ty", "appreciate"]
FAREWELLS = ["bye", "goodbye", "see ya", "later"]

DEFAULT_REPLY = N_(
    "I'm not sure about that one — I'm a simple built-in helper, not a full AI assistant. "
    "Try asking about expenses, triggers, interventions, goals, streaks, badges, family, currency, "
    "language, themes, or platform mode, or check the README for the full guide."
)
DEFAULT_REPLY_KID = N_(
    "Hmm, I don't know that one yet! Try asking me about adding spending, patterns, badges, "
    "your piggy bank, family, or themes. 🙂"
)

DEFAULT_SUGGESTIONS = [
    N_("How do I add an expense?"),
    N_("What is a trigger?"),
    N_("How do streaks and badges work?"),
    N_("How do I change the theme?"),
    N_("How does the Family page work?"),
]
DEFAULT_SUGGESTIONS_KID = [
    N_("How do I add spending?"),
    N_("What are patterns?"),
    N_("How do badges work?"),
    N_("What's my piggy bank?"),
]


def suggestions(kid: bool = False) -> List[str]:
    return [tr(x) for x in (DEFAULT_SUGGESTIONS_KID if kid else DEFAULT_SUGGESTIONS)]


def _words(text: str) -> List[str]:
    """Unicode-aware words, so Hindi, Tamil, Spanish… questions tokenize too."""
    return re.findall(r"[\w']+", text.lower())


def _normalize(word: str) -> str:
    """Very light stemming so plurals match their singular keyword (and
    vice versa) without a full NLP dependency: streaks->streak, badges->badge.
    Only applies to plain Latin words."""
    if not word.isascii():
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _tokenize(text: str) -> set:
    return {_normalize(w) for w in _words(text)}


def _extra(key: str) -> List[str]:
    """Translated keywords for this language ('kw:<english key>' in the catalog)."""
    val = tr("kw:" + key)
    return [] if val.startswith("kw:") else [v.strip().lower() for v in val.split("|") if v.strip()]


def _keyword_score(keyword: str, tokens: set) -> float:
    """Longer/more specific phrases score higher. Multi-word keywords match
    as long as every word appears somewhere in the message (not necessarily
    adjacent)."""
    words = _words(keyword)
    if not words:
        return 0.0
    if len(words) == 1:
        return 1.0 if _normalize(words[0]) in tokens else 0.0
    return 2.0 * len(words) if all(_normalize(w) in tokens for w in words) else 0.0


def _match_faq(tokens: set) -> Optional[Entry]:
    best_score, best_entry = 0.0, None
    for entry in FAQ_ENTRIES:
        kws = list(entry["keywords"]) + _extra(entry["keywords"][0])
        score = sum(_keyword_score(kw, tokens) for kw in kws)
        if score > best_score:
            best_score, best_entry = score, entry
    return best_entry


def _small_talk(kind: str, defaults: List[str]) -> List[str]:
    return defaults + _extra(kind)


def ask(message: str, platform_mode: str = "adult") -> Tuple[str, List[str]]:
    text = message.lower().strip()
    is_kid = platform_mode == "kid"

    # small talk, handled before the FAQ lookup so greetings don't get
    # swallowed by an unrelated keyword match
    words = _words(text)
    if words and words[0] in _small_talk("greetings", GREETINGS) and len(words) <= 3:
        reply = tr("Hey there! 👋 Ask me anything about using the app.") if is_kid else \
                tr("Hi! Ask me anything about how to use SpendSense-XAI.")
        return reply, suggestions(is_kid)
    if any(p in text for p in _small_talk("thanks", THANKS)):
        return (tr("You're welcome! 🎉") if is_kid else tr("You're welcome — happy to help.")), []
    if any(p in text for p in _small_talk("farewells", FAREWELLS)):
        return (tr("Bye! Come back if you need help. 👋") if is_kid else tr("Goodbye — come back any time.")), []

    tokens = _tokenize(text)
    entry = _match_faq(tokens)
    if entry is None:
        return tr(DEFAULT_REPLY_KID if is_kid else DEFAULT_REPLY), suggestions(is_kid)

    reply = entry.get("kid") if is_kid and entry.get("kid") else entry["default"]
    return tr(reply), []

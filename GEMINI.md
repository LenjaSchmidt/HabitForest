# Project briefing for the AI coding agent

You are helping a team of business students build a gamified habit-tracking MVP in Streamlit. The students have little coding background — write small, correct changes and explain them in plain English.

## The product

**HabitForest.** Users track daily habits. Instead of checklists and streak counters (boring), the reward is visual: a forest grows. Every completed habit contributes to a tree. Long streaks grow tall trees; broken streaks leave bare ground. The emotional metaphor is the product.

## Tech stack

- Python 3.10+
- Streamlit for the UI
- SQLite (stdlib `sqlite3`) for persistence — no external DB, no setup

No auth, no accounts, no mobile app. One local user, one database file.

## Data model

Two tables, created on first run:

```sql
CREATE TABLE habits (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE checkins (id INTEGER PRIMARY KEY, habit_id INTEGER, date TEXT);
```

`date` is always ISO `YYYY-MM-DD`. One check-in per habit per day — use `INSERT OR IGNORE` with a UNIQUE constraint if needed.

## House rules for changes

1. **Keep it one file.** `app.py` is the whole app.
2. **Use `st.markdown(..., unsafe_allow_html=True)` for SVG.** That's how you render custom graphics in Streamlit.
3. **For SVG trees: stay under 200 chars per tree string.** The forest renders many at once — keep it light.
4. **No charts library.** Use plain HTML/SVG in `st.markdown` for visual feedback. Plain text + emoji is also fine.
5. After every change, give the student one sentence: "now try clicking X and you should see Y".

## If you get stuck

If a feature is ambiguous, ask: "Is this an interaction with the database, or just a visual?" Visual-only features should never touch the DB.

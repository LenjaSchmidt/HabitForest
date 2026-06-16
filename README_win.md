# Kit – Group 4: HabitForest — Windows

Your MVP goal for today: **check a habit as "done today" → see a tree grow in your forest.**

That's the emotional core of your product. Everything else — Google Fit integration, tree-planting partnerships, levels — is scaffolding around this moment.

## What's in the box

```
starter/
  app.py            ← Streamlit app (<70 lines)
  habits.db         ← empty SQLite file (auto-created on first run)
  requirements.txt  ← streamlit only
```

## First run (≈3 minutes)

You need Python 3.10+. Check in PowerShell:

```powershell
python --version
```

If missing, install from https://python.org (not the Windows Store version — and tick "Add Python to PATH").

```powershell
cd starter

# create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# install and run
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens `http://localhost:8501`. You should see:

- An input to add a habit ("Drink water", "Read 10 pages", …)
- A list of today's habits with a "Done ✓" button each
- A simple forest view: one emoji tree per day you completed at least one habit

**This is deliberately ugly.** The first prompt will make it beautiful.

## Working with the AI agent

Open a **second** PowerShell window in the same `starter\` folder (leave Streamlit running in the first). In the second window:

```powershell
.\.venv\Scripts\activate
gemini          # or: claude
```

Then follow `prompts.md`. The first prompt turns the emoji trees into a real SVG that grows with your streak — that's the AHA moment.

## Troubleshooting

- **`streamlit: command not found`** → you forgot to activate the venv. Run `.\.venv\Scripts\activate` first.
- **`python` not found but `py` works** → use `py -m venv .venv` and `py -m pip install ...` instead.
- **PowerShell blocks script execution** → one-time fix: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
- **SQLite "database is locked"** → close any other Streamlit tabs, restart the server. Last resort: delete `habits.db` and start over.
- **Port 8501 already in use** → `streamlit run app.py --server.port 8502`.

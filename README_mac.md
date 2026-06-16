# Kit – Group 4: HabitForest — macOS

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

You need Python 3.10+. Check in the Terminal:

```bash
python3 --version
```

macOS often ships with 3.9. If yours is below 3.10, ask the AI agent: *"Install a recent Python on macOS for me."* It'll guide you through Homebrew.

```bash
cd starter

# create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

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

Open a **second** Terminal tab in the same `starter/` folder (leave Streamlit running in the first). In the second tab:

```bash
source .venv/bin/activate
gemini          # or: claude
```

Then follow `prompts.md`. The first prompt turns the emoji trees into a real SVG that grows with your streak — that's the AHA moment.

## Troubleshooting

- **`streamlit: command not found`** → you forgot to activate the venv. Run `source .venv/bin/activate` first.
- **`python: command not found`** → on macOS use `python3` (and `pip3`). Inside the venv, plain `python` works.
- **SQLite "database is locked"** → close any other Streamlit tabs, restart the server. Last resort: delete `habits.db` and start over.
- **Port 8501 already in use** → `streamlit run app.py --server.port 8502`.

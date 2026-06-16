# Your three prompts for today

Copy each one into Gemini CLI (or Claude Code) in order. Read the diff after each.

---

## Prompt 1 — The AHA moment

> Replace the emoji trees in the forest view with real SVG trees. A tree's height should depend on how many habits were completed on that day: 1 habit = small sprout, 2-3 habits = medium tree, 4+ habits = tall tree with a leafy crown. Render all trees side by side in a single row using `st.markdown` with `unsafe_allow_html=True`. Use green tones.

This is the screenshot your team will put on the poster. Take the screenshot *before* Prompt 2 breaks something.

---

## Prompt 2 — The real feature

> Add a "current streak" counter at the top of the page, showing the number of consecutive days (ending today) where at least one habit was completed. If I miss a day, the streak resets. Display it big, above everything else, as `st.metric("🔥 Current streak", "X days")`.

Testing tip: the starter has no check-ins yet, so before this feature will show anything, click "Done" on a few habits. To fake history for testing: ask the agent to add 3 rows directly to `checkins` with dates from the last few days.

---

## Prompt 3 — The ambitious one (if time allows)

> Add a "milestone" system. When the current streak hits 7 days, show a big "🌳 You've planted a real tree!" message at the top and play a little confetti animation (`st.balloons()` works). The message should only show on the day the milestone is first reached, not forever — use `st.session_state` to track whether we've already shown it this session.

This is your hook into the "real-world tree planting" business model — the UI already assumes partnerships exist.

---

## What to do when things break

- If SQLite complains "database is locked", close other Streamlit tabs and restart the server
- If you want a fresh start: delete `habits.db` and refresh
- SVG not rendering? Check you passed `unsafe_allow_html=True` to `st.markdown`

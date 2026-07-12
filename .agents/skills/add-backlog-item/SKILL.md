---
name: add-backlog-item
description: Capture a requested feature, bug, investigation, or idea in this project's canonical backlog without implementing it. Use when the user says "add item to back log", "add this to the backlog", "backlog this", "remember this for later", or invokes $add-backlog-item.
---

# Add Backlog Item

1. Read `plan/backlog.md` headings and search the file for the concept, synonyms, and related item numbers.
2. If it already exists, update that item with the new evidence or requirement instead of creating a duplicate.
3. Otherwise place it in the closest thematic section. If no section fits, add the next numbered section immediately before `## Outstanding`.
4. Record only what is known:
   - concise outcome-oriented title;
   - source and date, including a short user quote when useful;
   - observed problem or opportunity;
   - desired behavior;
   - acceptance evidence;
   - dependencies and open decisions;
   - classification: `loop-safe`, `live/PIE`, `C++/editor`, or `design decision`.
5. Put actionable priority in the active queue only when the user supplied priority or dependencies make the order unambiguous. Otherwise leave it in its thematic section for grooming.
6. Preserve historical status notes. Do not implement code, create a spec, promise dates, or mark the item approved without explicit evidence.
7. Report the item number/section and a one-sentence summary of what was recorded.

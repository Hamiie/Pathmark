# Pathmark Release Hub

This release combines Calendar and Tasks into a single Google Sync workflow, keeps Pathmark as the planning source of truth for linked Google items, renames the hosted planner to Pathmark Planner, and improves printable tasklists so supporting time blocks are indented under their focus block with cleaner notes/context.

## v0.6.92 Google Sync and printable tasklist hierarchy

- Preloads the revised default Areas for fresh Pathmark Sync sheets.
- Keeps Project planning style as **Task-based** or **Focus-based**, with the project steps panel adapting to the selected mode.
- Prevents a focus-based project being switched back to task-based while focus blocks exist.
- Excludes supporting time blocks and helper checklist items from project completion/progress while still allowing them to create Google Tasks checklist items.
- Updates Dashboard and Projects progress wording to refer to project progress items.
- Preserves v0.6.90 consolidated Meal Plan starter-pack import support.

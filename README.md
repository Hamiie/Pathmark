# Pathmark v0.7.28 — Native workspace navigation fix

Fixes the signed-in workspace tile navigation from v0.7.27. Workspace tiles now use native Streamlit state changes instead of HTML query-string links, so Planning, Nutrition and Finance open their correct focused workspaces rather than falling back to the default Planning dashboard.

Workspace switcher controls inside Planning, Nutrition and Finance now also use native state changes.

No new Supabase migration is needed for this version.

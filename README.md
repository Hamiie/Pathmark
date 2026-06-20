# Pathmark v0.7.29 — Loading states and interaction guard

Adds a restrained loading and interaction-guard pattern for the signed-in Pathmark shell. Opening Pathmark Home, Planning, Nutrition, Finance, Appearance, About & Privacy, Public Home / Download or Developer now sets a native Streamlit loading state and shows a quiet status strip while the target page prepares.

Workspace tiles and in-workspace switcher controls remain native Streamlit navigation actions. The old HTML/query-string workspace routing has not been reintroduced.

No new Supabase migration is needed for this version.

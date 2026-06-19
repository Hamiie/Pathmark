# Pathmark v0.7.27 — OAuth callback guard and workspace UX polish

Polishes the signed-in Pathmark shell introduced in v0.7.26. Workspace cards on Pathmark Home now behave as clickable tiles, utilities are visually quieter, and focused workspaces use lighter breadcrumb/switcher navigation instead of a large back button.

This version also guards Google OAuth callback handling. Stale or already-used Google sign-in URLs are cleared from the address bar and shown as a gentle notice rather than a red first-load error.

No new Supabase migration is needed for this version.

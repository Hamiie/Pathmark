-- v0.5.90
-- Store a small, non-sensitive UI preference with the user's Pathmark access profile.
-- This keeps the online theme consistent when a user logs in on another device.
-- No personal planning data is stored in Supabase.

alter table public.pathmark_users
  add column if not exists theme_preference text not null default 'Default';

alter table public.pathmark_users
  drop constraint if exists pathmark_users_theme_preference_check;

alter table public.pathmark_users
  add constraint pathmark_users_theme_preference_check
  check (theme_preference in ('Default', 'Sage', 'Blue', 'Plum', 'Warm'));

# Pathmark v0.7.30 Supabase templates

These CSV headers support the v0.7.30 ingredient conversion and recipe alternative model.

Recommended use:

1. Upload canonical ingredients and aliases first.
2. Upload `pathmark_ingredient_unit_conversions` for shared volume/count/household-measure conversions.
3. Upload recipe starter-pack data either through `pathmark_starter_pack_rows` or, later, the structured group/option tables.
4. Keep starter packs inactive until the converted data has been reviewed.

The app still stores user-specific recipe, shopping, inventory and override data in the user's Pathmark Sync Google Sheet. These Supabase tables are for shared Pathmark reference data and optional starter-pack/library data.

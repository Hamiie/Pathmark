# Pathmark v0.7.30 — Ingredient conversions and recipe alternatives

Adds the foundation for a cleaner ingredient model in the hosted Pathmark app.

## Main changes

- Adds ingredient-specific unit conversions so Pathmark can convert volume, household and count measures into an ingredient's preferred calculation unit where a conversion exists.
- Stops treating every millilitre as if it were a gram for nutrition and cost estimates.
- Adds a user conversion table in Pathmark Sync: `ingredient_unit_conversions`.
- Adds structured recipe ingredient groups and options in Pathmark Sync:
  - `recipe_ingredient_groups`
  - `recipe_ingredient_options`
- Updates Recipe Library so a recipe ingredient can have a structured alternative.
- Updates quick ingredient entry to recognise explicit `or` / `and/or` alternatives and save them as options.
- Updates Meal Plan to carry alternatives into shopping lists.
- Updates Shopping List so the user can select an alternative before adding trolley items to inventory.
- Keeps the actual selected/bought ingredient as the item that flows into inventory.
- Adds a Supabase migration and blank CSV headers for shared conversion and recipe-option reference data.

## Notes

This release keeps older recipe rows compatible. Existing `recipe_ingredients` rows still work, while new rows can carry structured group/option metadata.

User-specific conversions and selections remain in the user's own Pathmark Sync Google Sheet. Supabase is used for shared Pathmark reference data and optional starter-pack/library data.

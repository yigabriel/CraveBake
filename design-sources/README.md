# Design sources

Original, full-size artwork that the app is built from. It is **not** served: only
the optimized files in `frontend/public/` are published.

- `auth_page/` — the 2736x1536 PNG layers of the sign-in scene (background + one per dessert).
  The WebP files in `frontend/public/images/auth-scene/` are cut from these, and `BOXES` in
  `frontend/src/components/DessertScene.tsx` holds the visible area of each layer.

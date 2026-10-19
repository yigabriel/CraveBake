---
name: Pastry
colors:
  surface: '#fff8f6'
  surface-dim: '#e8d6d2'
  surface-bright: '#fff8f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1ed'
  surface-container: '#fceae6'
  surface-container-high: '#f6e4e0'
  surface-container-highest: '#f0dfda'
  on-surface: '#221917'
  on-surface-variant: '#55423e'
  inverse-surface: '#382e2b'
  inverse-on-surface: '#ffede9'
  outline: '#88726d'
  outline-variant: '#dbc1ba'
  surface-tint: '#9a442d'
  primary: '#9a442d'
  on-primary: '#ffffff'
  primary-container: '#e07a5f'
  on-primary-container: '#5b1604'
  inverse-primary: '#ffb4a1'
  secondary: '#795741'
  on-secondary: '#ffffff'
  secondary-container: '#fed1b5'
  on-secondary-container: '#795842'
  tertiary: '#386753'
  on-tertiary: '#ffffff'
  tertiary-container: '#70a18a'
  on-tertiary-container: '#003725'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd2'
  primary-fixed-dim: '#ffb4a1'
  on-primary-fixed: '#3c0800'
  on-primary-fixed-variant: '#7c2e19'
  secondary-fixed: '#ffdcc6'
  secondary-fixed-dim: '#e9bea2'
  on-secondary-fixed: '#2d1605'
  on-secondary-fixed-variant: '#5e402b'
  tertiary-fixed: '#bbeed4'
  tertiary-fixed-dim: '#9fd1b8'
  on-tertiary-fixed: '#002115'
  on-tertiary-fixed-variant: '#1f4f3c'
  background: '#fff8f6'
  on-background: '#221917'
  surface-variant: '#f0dfda'
typography:
  display-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Be Vietnam Pro
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Be Vietnam Pro
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  gutter: 24px
  margin-mobile: 20px
  margin-desktop: 64px
---

## Brand & Style
The design system is built on a foundation of "Warm Editorial Minimalism." It is designed to feel like a high-end culinary magazine—sophisticated yet deeply inviting. The target audience includes home bakers and professional pastry chefs who appreciate precision and aesthetics. 

The aesthetic blends **Modern Corporate** reliability with **Minimalist** clarity. It prioritizes high-quality food photography as a core UI element, treating images not as decoration, but as the primary information carrier. The UI is quiet, allowing the textures of flour, butter, and fruit to take center stage, supported by a tactile sense of depth and soft, organic shapes.

## Colors
The palette is grounded in the organic tones of the baking process.
- **Primary (Burnt Peach):** Used for essential actions, progress indicators, and interactive highlights. It represents the "golden hour" of a perfect bake.
- **Secondary (Dark Coffee):** The anchor for all communication. Used for high-contrast typography and iconography to ensure legibility and a premium feel.
- **Background (Eggshell):** A soft, off-white surface that reduces eye strain and provides a warmer, more culinary feel than pure white.
- **Accents:** **Muted Teal** serves as a sophisticated functional color for success states and health/dietary indicators. **Apricot Cream** is used for secondary containers, providing a soft lift against the Eggshell background.

## Typography
This design system utilizes **Be Vietnam Pro** to achieve a modern, friendly, and sophisticated editorial look. 
- **Headlines:** Use tight letter-spacing and bold weights for a confident, "top-chef" authoritative feel.
- **Body:** Generous line-height is essential to maintain the breezy, editorial flow of recipe instructions.
- **Labels:** Small labels use a slightly higher font weight and increased tracking for clarity when used in metadata (e.g., prep time, difficulty level).
- **Scale:** On mobile, display sizes are reduced to ensure headlines do not break awkwardly, maintaining the "magazine cover" composition.

## Layout & Spacing
The layout follows a **Fluid Grid** model with an emphasis on "negative space as a luxury."
- **Desktop:** A 12-column grid with wide margins (64px) and generous gutters (24px). Content should be centered with significant breathing room on the flanks.
- **Mobile:** A 4-column grid with 20px margins. 
- **Rhythm:** Use the 8px base unit. For recipe steps and ingredient lists, use `md` (24px) spacing to prevent the UI from feeling cluttered. For section transitions, use `xl` (80px) to clearly signal a shift in content (e.g., from "Story" to "Recipe").

## Elevation & Depth
This design system uses a **Tonal Layering** approach combined with **Ambient Shadows**. 
- **Level 0 (Base):** Eggshell (#F4F1DE).
- **Level 1 (Cards/Surfaces):** Apricot Cream (#F2CC8F) or White with a very soft, diffused shadow (10% opacity Burnt Peach tint, 20px blur, 4px Y-offset).
- **Interactive Depth:** Buttons and active cards should use a "lift" effect—increasing the shadow blur on hover to simulate physical proximity to the user. 
- **Overlays:** Use a subtle backdrop blur (8px) for modals to maintain the warmth of the underlying food photography without sacrificing text legibility.

## Shapes
Shapes in this design system are purposefully **Rounded** to evoke the softness of dough and organic culinary forms.
- **Standard (0.5rem):** Used for input fields and smaller buttons.
- **Large (1rem):** Used for recipe cards, image containers, and modal windows.
- **Extra Large (1.5rem):** Reserved for "Hero" cards and promotional banners to create a soft, inviting focal point.
- **Interactive Elements:** Checkboxes and radio buttons should maintain a soft-square or circle profile to match the overall friendliness.

## Components
- **Buttons:** Primary buttons are Burnt Peach with White text. Use a large 0.5rem radius. For secondary actions, use "Ghost" buttons with a Dark Coffee outline.
- **Recipe Cards:** Use Level 1 elevation with 1rem rounded corners. The image should occupy the top 60% of the card, using an "aspect-ratio: 4/3".
- **Chips/Badges:** Use Apricot Cream backgrounds with Dark Coffee text for categories (e.g., "Vegan", "Gluten-Free"). Use Muted Teal for "Success" or "Verified" badges.
- **Input Fields:** Eggshell background with a subtle 1px Dark Coffee border at 20% opacity. Focus state should transition the border to Burnt Peach.
- **Lists:** Ingredient lists should have a custom check-mark in Burnt Peach. Use `sm` (12px) vertical padding between list items to ensure tap targets are accessible.
- **Specialty Component (The Timer):** A circular, "floating" timer component using a Muted Teal stroke to track baking progress, anchored to the bottom-right of the viewport.
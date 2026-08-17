---
name: Liquid Gold Directives
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#37393a'
  surface-container-lowest: '#0c0f0f'
  surface-container-low: '#1a1c1c'
  surface-container: '#1e2020'
  surface-container-high: '#282a2b'
  surface-container-highest: '#333535'
  on-surface: '#e2e2e2'
  on-surface-variant: '#d0c5af'
  inverse-surface: '#e2e2e2'
  inverse-on-surface: '#2f3131'
  outline: '#99907c'
  outline-variant: '#4d4635'
  surface-tint: '#e9c349'
  primary: '#f2ca50'
  on-primary: '#3c2f00'
  primary-container: '#d4af37'
  on-primary-container: '#554300'
  inverse-primary: '#735c00'
  secondary: '#c8c6c7'
  on-secondary: '#303031'
  secondary-container: '#49494a'
  on-secondary-container: '#bab8b9'
  tertiary: '#d0cdce'
  on-tertiary: '#303031'
  tertiary-container: '#b4b2b3'
  on-tertiary-container: '#454546'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffe088'
  primary-fixed-dim: '#e9c349'
  on-primary-fixed: '#241a00'
  on-primary-fixed-variant: '#574500'
  secondary-fixed: '#e5e2e3'
  secondary-fixed-dim: '#c8c6c7'
  on-secondary-fixed: '#1b1b1c'
  on-secondary-fixed-variant: '#474647'
  tertiary-fixed: '#e4e2e3'
  tertiary-fixed-dim: '#c8c6c7'
  on-tertiary-fixed: '#1b1b1c'
  on-tertiary-fixed-variant: '#474648'
  background: '#121414'
  on-background: '#e2e2e2'
  surface-variant: '#333535'
typography:
  display-lg:
    fontFamily: Libre Caslon Text
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Libre Caslon Text
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Libre Caslon Text
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
  headline-sm:
    fontFamily: Libre Caslon Text
    fontSize: 24px
    fontWeight: '400'
    lineHeight: 32px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-desktop: 64px
  margin-mobile: 20px
---

## Brand & Style

The design system is engineered for **PourMind**, a dual-facing mixology platform catering to both the curious home consumer and the seasoned bar professional. The brand personality is rooted in **Expertise, Seamlesness, and Exclusivity**. It evokes the atmosphere of a high-end speakeasy: intimate, precise, and premium.

The visual style is a fusion of **Corporate Modern** precision and **Glassmorphism** elegance. It prioritizes high-fidelity photography, allowing the vibrant colors of spirits and cocktails to serve as the primary visual interest against a disciplined, dark-mode foundation. Every interaction should feel intentional and high-touch, reflecting the craft of mixology itself.

## Colors

This design system utilizes a "Noir & Gold" palette to establish an immediate sense of luxury.

- **Primary (Amber/Gold):** Used sparingly for calls-to-action, active states, and subtle accents. It represents the warmth and quality of aged spirits.
- **Secondary (Deep Charcoal):** The primary canvas. This deep, near-black shade provides the necessary depth for glassmorphism effects to excel.
- **Tertiary (Graphite):** Used for surface elevation, card backgrounds, and secondary containers to create subtle tonal separation.
- **Neutral (Optical White):** Reserved strictly for typography and iconography to ensure maximum legibility and a clean, technical feel.

Use gradients of the Primary color (Amber to a deeper Bronze) only for high-impact display elements or B2B data visualizations.

## Typography

The typography strategy employs a "Classic/Modern" contrast. 

**Libre Caslon Text** is used for all headlines and display text. Its editorial weight and sharp serifs provide an authoritative, "library-esque" feel suitable for recipe titles and expert articles.

**Hanken Grotesk** serves as the workhorse for all UI elements, data tables, and body copy. It is a sharp, contemporary sans-serif that ensures clarity in professional B2B dashboards and mobile recipe lists.

- Use **Label-MD** (uppercase with tracking) for section headers and button text to maintain a disciplined, architectural look.
- Maintain generous line-heights in body copy to prevent the dark background from feeling claustrophobic.

## Layout & Spacing

The layout follows a **Fixed Grid** philosophy on desktop to preserve the "boutique" feel, while transitioning to a **Fluid Grid** on mobile for maximum utility.

- **Desktop:** 12-column grid, 1280px max width. Use wide margins (64px) to create a sense of exclusivity and breathing room.
- **Tablet:** 8-column grid with 32px margins.
- **Mobile:** 4-column grid with 20px margins.

Spacing is based on an **8px base unit**. Component internal padding should favor larger vertical gaps (16px, 24px) to emphasize the verticality of cocktail glassware and tall bottles. Photography should often break the grid or bleed to the edges to create a cinematic experience.

## Elevation & Depth

This design system rejects heavy shadows in favor of **Glassmorphism and Tonal Layering**. 

Depth is communicated through:
1.  **Backdrop Blurs:** High-level surfaces (modals, navigation bars) use a 20px-30px backdrop blur with a 10% white tint.
2.  **Gold Hairlines:** Instead of shadows, use 1px borders in `#D4AF37` at 20% opacity to define the edges of cards and containers.
3.  **Luminance Stacking:** The background is `#1A1A1B`. Primary cards are `#2D2D2E`. Secondary pop-overs are slightly lighter. This creates depth without relying on artificial lighting.
4.  **Selective Glow:** Only the most critical action buttons may have a subtle, soft-amber outer glow to simulate light passing through a liquid.

## Shapes

The shape language is **Soft (0.25rem / 4px)**. 

While the "rounded" or "pill" trends are popular, this design system uses tighter radii to maintain a professional, high-end precision. 
- **Standard UI (Inputs, Buttons):** 4px radius.
- **Containers (Cards, Modals):** 8px radius (`rounded-lg`).
- **Media (Cocktail Photos):** 12px radius (`rounded-xl`) to soften the edges of the lifestyle imagery.

Avoid fully rounded "pill" buttons; the subtle 4px corner maintains a more architectural and "custom-built" aesthetic.

## Components

### Buttons
- **Primary:** Solid `#D4AF37` with black text. No border.
- **Secondary:** Transparent with a 1px `#D4AF37` border (20% opacity) and gold text.
- **B2B Utility:** Ghost buttons with white text for dashboard actions.

### Input Fields
Dark backgrounds (`#2D2D2E`) with a bottom-only 1px white border. On focus, the border transitions to Gold. Labels sit above the field in **Label-SM**.

### Cards
Cards use the glassmorphic style. Background: `rgba(45, 45, 46, 0.7)`. Border: 1px `rgba(212, 175, 55, 0.15)`. All cards housing cocktail images should use an aspect ratio of 4:5 or 1:1.

### Data Visualizations (B2B)
For bar professionals, use thin-line charts. The "Hot" or "High Performance" data should be Gold, while "Baseline" data should be a muted Grey. Avoid multi-colored rainbows; stick to the brand palette.

### Chips/Tags
Used for flavor profiles (e.g., "Smoky", "Citrus"). Small, 4px rounded, with a subtle `#2D2D2E` fill and white text. No borders to keep them secondary to the main content.
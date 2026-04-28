# Midnight Gavel: Design System

### 1. Overview & Creative North Star
**Creative North Star: The Sovereign Sentinel.**
Midnight Gavel is a high-end editorial design system tailored for judicial and investigative environments. It moves away from the "app-like" clutter of standard administrative software toward a sophisticated, data-driven editorial layout. The system uses a disciplined color palette and sharp geometry to convey authority, precision, and the weight of truth. It breaks traditional patterns through **Intentional Asymmetry**—where sidebars and main content areas use contrasting densities—and **Tonal Depth** to signify investigative urgency.

### 2. Colors
The palette is rooted in deep navy (#001E40) and cool slate, accented by a striking tertiary red (#BA1A1A) for critical "collision" events.

*   **The "No-Line" Rule:** Sectioning is achieved through background shifts. For example, the `surface-container-low` (#F2F4F7) main area is distinct from the `surface-container-lowest` (#FFFFFF) data cards without the need for rigid 1px borders.
*   **Surface Hierarchy:**
    *   **Background:** #F7F9FC (Base layer)
    *   **Navigation:** #D8DADD (Low depth, high stability)
    *   **Data Panels:** #FFFFFF (Maximum focus/clarity)
*   **Glass & Gradient Rule:** Floating toolbars or overlays should utilize `glass-panel` properties (60% opacity with 20px blur) to maintain context.
*   **Signature Textures:** Primary CTAs use a linear gradient from `primary` to `primary-container` to add a sense of premium "finish."

### 3. Typography
The system utilizes a high-contrast pairing of **Public Sans** for structure and **Inter** for data readability.

*   **Display/Headline:** Public Sans (Bold/Black). Uses tight tracking and uppercase styling for top-level navigation to command attention.
*   **Body/Label:** Inter. Optimized for high-density information.
*   **The Scale (Extracted Truth):**
    *   **Large Titles:** 1.5rem (24px) for page headers.
    *   **Subheaders:** 1.125rem (18px) for primary section labels.
    *   **Standard Body:** 0.875rem (14px).
    *   **Small/Metadata:** 0.75rem (12px) to 10px for technical identifiers (e.g., "DATA_NODE").
    *   **Micro-Labels:** 8px for non-critical timestamps or grid reference points.

### 4. Elevation & Depth
Midnight Gavel replaces drop-shadow-heavy designs with **Tonal Layering**.

*   **The Layering Principle:** Depth is created by stacking lighter surfaces (`lowest`) on top of muted backgrounds (`low`).
*   **Ambient Shadows:** We utilize "Shadow-LG" for floating export buttons and "Shadow-SM" for data points. Shadows are never pure black; they use 4-5% opacity of the `primary` color (rgba(0,30,64,0.05)) to feel integrated rather than "pasted on."
*   **Glassmorphism:** Use `backdrop-filter: blur(20px)` for high-level toolbars to imply a sophisticated, layered digital workspace.

### 5. Components
*   **Buttons:** Rectangular with minimal rounding (2px to 8px). Primary buttons use the "Midnight Gradient." Secondary buttons use ghost styling with subtle `outline-variant` borders.
*   **Timeline Tracks:** Use a `tonal-line` (4px wide, `surface-variant`) for vertical flow. Horizontal tracks use `hover:bg-surface-container-low/50` for interactive feedback.
*   **Status Chips:** Pill-shaped, high-contrast. Tertiary-red for high-risk warnings; Primary-blue for information.
*   **Bento Grid Cards:** Information should be grouped in "Bento" style boxes with inconsistent widths to create an editorial, non-templated look.

### 6. Do's and Don'ts
*   **Do:** Use vertical accent lines (e.g., a 4px `primary` strip) on the left of cards to denote active selection or category.
*   **Do:** Maintain high whitespace in headers while using tight density for actual data grids.
*   **Don't:** Use rounded corners exceeding 12px (except for icons). The system thrives on "near-sharp" geometry.
*   **Don't:** Introduce vibrant "consumer" colors like bright green or orange. Stick to the Judicial Red and Sovereign Navy.
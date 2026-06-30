---
tokens:
  colors:
    brand:
      primary: "#ff4d00"
      primary-5: "rgba(255,77,0,0.05)"
      primary-10: "rgba(255,77,0,0.10)"
    surface:
      app-bg: "#f8f9fa"
      card: "#ffffff"
      input-bg: "#f8fafc"
    text:
      primary: "#1a1a1a"
      secondary: "#6b7280"
      muted: "#a8a29e"
      inverse: "#ffffff"
    border:
      default: "#e7e5e4"
      subtle: "#f5f5f4"
    feedback:
      success-bg: "#ff4d00"
      success-text: "#ffffff"
      error-bg: "#fff1f2"
      error-text: "#9f1239"
      error-border: "#fda4af"
      info-bg: "#f5f5f4"
      info-text: "#292524"
      info-border: "#d6d3d1"
    step:
      active: "#ff4d00"
      completed: "#16a34a"
      pending: "#d6d3d1"
  typography:
    fontFamily:
      sans: '"Inter", ui-sans-serif, system-ui, sans-serif'
      mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, monospace'
      serif: '"Lora", "Georgia", ui-serif, serif'
    fontSize:
      label-xs: "10px"
      label-sm: "10.5px"
      body-xs: "11px"
      body-sm: "11.5px"
      body: "12px"
      body-md: "13px"
      heading-sm: "15px"
      heading-md: "17px"
    fontWeight:
      normal: 400
      medium: 500
      semibold: 600
      bold: 700
      extrabold: 800
    letterSpacing:
      label: "0.18em"
      wide: "0.2em"
      wider: "0.25em"
      widest: "0.3em"
  spacing:
    sidebar-width: "256px"
    header-height: "64px"
    panel-padding: "24px"
    gap-xs: "4px"
    gap-sm: "8px"
    gap-md: "12px"
    gap-lg: "16px"
    gap-xl: "24px"
    gap-2xl: "32px"
  radius:
    none: "0px"
  shadow:
    card: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)"
    modal: "0 25px 50px -12px rgba(0,0,0,0.25)"
    focus-ring: "0 0 0 1px #ff4d00"
  components:
    Button:
      variants:
        - name: primary
          bg: "#0c0a09"
          text: "#ffffff"
          hover-bg: "#1c1917"
          style: "uppercase tracking-wider font-mono font-bold text-[10px] px-5 py-2.5 rounded-none"
        - name: danger
          bg: "#ff4d00"
          text: "#ffffff"
          style: "uppercase tracking-wider font-mono font-bold text-[10px] px-5 py-2.5 rounded-none"
        - name: ghost
          text: "#6b7280"
          hover-text: "#0c0a09"
          style: "uppercase tracking-wider font-mono text-[10px] bg-transparent rounded-none"
        - name: muted
          bg: "#f5f5f4"
          text: "#292524"
          hover-bg: "#e7e5e4"
          style: "rounded-none text-[10px] font-mono uppercase tracking-wider"
    Input:
      base: "bg-stone-50 text-stone-900 border border-stone-200 rounded-none px-3 py-2 text-xs font-mono outline-none"
      focus: "focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00]"
      placeholder: "placeholder:text-stone-400"
    SidebarNav:
      width: "256px"
      item-active: "bg-[#ff4d00]/5 text-[#ff4d00] border-l-2 border-[#ff4d00]"
      item-default: "text-stone-600 hover:bg-stone-50 hover:text-stone-950"
      item-style: "rounded-none text-xs uppercase tracking-wider font-semibold px-4 py-3"
    StepIndicator:
      connector: "border-t-2 border-stone-200"
      dot-active: "bg-[#ff4d00] text-white"
      dot-completed: "bg-green-600 text-white"
      dot-pending: "bg-stone-200 text-stone-500"
      label-active: "text-[#ff4d00] font-bold"
      label-pending: "text-stone-400"
    Badge:
      happy: "bg-blue-50 text-blue-700 border border-blue-200"
      edge: "bg-rose-50 text-rose-700 border border-rose-200"
      support: "bg-amber-50 text-amber-700 border border-amber-200"
      generated: "bg-stone-100 text-stone-600 border border-stone-200"
    Toast:
      base: "px-5 py-3 flex items-center gap-2.5 text-[10px] font-mono uppercase tracking-widest border shadow-xl"
      success: "bg-[#ff4d00] text-white border-[#ff4d00]"
      error: "bg-rose-100 text-rose-800 border-rose-300"
      info: "bg-stone-100 text-stone-800 border-stone-300"
    Table:
      header: "bg-stone-50 text-[10px] font-bold uppercase tracking-widest text-stone-500 font-mono border-b border-stone-200"
      row: "border-b border-stone-100 hover:bg-stone-50/70 transition-colors"
      cell: "px-4 py-3 text-xs text-stone-700"
    Modal:
      overlay: "bg-stone-900/40 backdrop-blur-[2px]"
      box: "bg-white border border-stone-200 shadow-2xl rounded-none"
      header: "border-b border-stone-100 pb-4"
      footer: "border-t border-stone-100 pt-5"
---

# DESIGN.md — AI Test Case Generator

Design system specification for the AI Test Case Generator frontend. Codifies the existing visual language so that AI coding agents and contributors can build new components consistent with the established aesthetic.

---

## 1. Philosophy

The UI intentionally adopts a **sharp, enterprise-grade, monospace-heavy** aesthetic — reminiscent of a professional dev tool or terminal-native application. Key principles:

- **Zero border-radius** (`rounded-none`) everywhere. Sharp edges signal precision.
- **Mono everywhere functional** — all labels, inputs, buttons, and status indicators use `font-mono` + `uppercase` + `tracking-widest` to feel systematic and machine-authoritative.
- **Serif for narrative** — `font-serif italic` (Lora) appears only in descriptive sub-labels and rationale text to contrast with the mechanical mono layer.
- **One brand color** — `#ff4d00` (vibrant orange-red) is the single expressive accent. It marks active states, CTAs, the brand logo, and success toasts. Everything else is in the stone/neutral palette.
- **Density-first layout** — small font sizes (10–13px) allow high information density without visual clutter.

---

## 2. Color Usage

### Brand Accent (`#ff4d00`)
Used sparingly but decisively:
- Sidebar nav active item: left border + text + faint background tint (`/5`)
- Focus ring on all interactive inputs
- Primary CTA buttons (reserved for key actions)
- Active tab underline in modals and step tabs
- Brand logo mark background
- Success toast background (reinforces "action succeeded" with energy)
- Animated status indicator pulse in the header

### Surfaces
- **App background**: `#f8f9fa` — off-white, not pure white, reduces eye strain during long sessions
- **Sidebar / Header / Cards**: `#ffffff` — pure white to float against the app background
- **Input / select backgrounds**: `stone-50` — slightly warm to distinguish from pure card backgrounds

### Stone Neutral Scale
All secondary UI uses Tailwind's `stone-*` palette (warm-leaning grays):
- `stone-950` / `stone-900` — primary text, primary button backgrounds
- `stone-500` / `stone-600` — secondary labels, muted icons
- `stone-200` / `stone-300` — borders, dividers
- `stone-50` — hover states, subtle backgrounds

---

## 3. Typography

Three font families serve distinct roles:

| Family | Variable | Role |
|--------|----------|------|
| Inter | `font-sans` | Default body, prose, long-form |
| JetBrains Mono | `font-mono` | Labels, inputs, badges, buttons, status text |
| Lora | `font-serif italic` | Descriptive sub-labels, rationale copy only |

### Type Scale
Labels and UI chrome use pixel values, not rem, for precise density control:
- `text-[10px]` — micro labels, button text
- `text-[10.5px]` — header breadcrumb, status indicators
- `text-xs` (12px) — inputs, table cells, general body
- `text-[13px]` — section titles, card headers
- `text-[17px]` — brand title in sidebar

All mono text in UI chrome: `uppercase tracking-widest font-bold` or `font-semibold`.

---

## 4. Layout

```
┌──────────────────────────────────────────────────────────┐
│ Sidebar (256px fixed)    │ Header (h-16 sticky)          │
│  - Brand logo            │  - Workspace label (mono)     │
│  - Nav items             │  - Status indicator (pulse)   │
│  - Settings (API/Domain) │                               │
│  - Footer links          ├───────────────────────────────┤
│                          │ StepIndicator                 │
│                          ├───────────────────────────────┤
│                          │ Tab Content (full flex-1)     │
│                          │  Step 1: Data Ingestion       │
│                          │  Step 2: Intent Curation      │
│                          │  Step 3: Persona Playground   │
│                          │  Step 4: Export & Test Cases  │
│                          ├───────────────────────────────┤
│                          │ Utility row (reset / info)    │
└──────────────────────────────────────────────────────────┘
```

Main content area: `pl-64` offset for fixed sidebar, `p-8` internal padding.

---

## 5. Component Patterns

### Inputs
All inputs and selects share the same base class:
```
bg-stone-50 text-stone-900 border border-stone-200 rounded-none px-3 py-2 text-xs
focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none font-mono
```
No border radius. Brand focus ring.

### Buttons

**Primary action** (dark):
```
bg-stone-950 text-white rounded-none px-5 py-2.5
text-[10px] font-bold uppercase tracking-wider font-mono
hover:bg-stone-800 disabled:opacity-50
```

**Brand CTA** (orange-red):
```
bg-[#ff4d00] text-white rounded-none px-5 py-2.5
text-[10px] font-bold uppercase tracking-wider font-mono
```

**Ghost**:
```
bg-transparent text-stone-400 hover:text-stone-800 rounded-none
text-[10px] font-bold uppercase tracking-wider font-mono
```

### Tables
Header row: `bg-stone-50`, mono uppercase labels, `border-b border-stone-200`.  
Data rows: `border-b border-stone-100`, hover `bg-stone-50/70`.  
No rounded corners on table or cells.

### Modals
Overlay: `bg-stone-900/40 backdrop-blur-[2px]`  
Box: `bg-white border border-stone-200 shadow-2xl rounded-none`  
Enter animation: `opacity: 0→1, scale: 0.95→1, y: 15→0` over 200ms ease-out.

### Toast Notifications
Fixed top-right, no border-radius:
- **Success** → `bg-[#ff4d00] text-white` (brand orange-red)
- **Error** → `bg-rose-100 text-rose-800 border-rose-300`
- **Info** → `bg-stone-100 text-stone-800 border-stone-300`

All toasts: `font-mono uppercase tracking-widest text-[10px]`. Auto-dismiss after 4 seconds.

### Step Indicator
4 steps connected by a `border-t-2 border-stone-200` line.  
Dot states: active (brand color), completed (green-600), pending (stone-200).  
Labels below dots: mono uppercase, active in brand color.

---

## 6. Icons

Uses **Material Symbols Outlined** (Google Fonts icon font) exclusively.  
Size convention: `text-[16px]` inline in labels, `text-[20px]` in nav items, `text-[22px]` in brand logo.  
`select-none` on all icon spans to prevent text selection.

---

## 7. Animation

Uses the `motion` package (Framer Motion fork). Standard values:
- Modal enter/exit: `duration: 0.2, ease: "easeOut"`
- Properties: `opacity`, `scale` (0.95→1), `y` (15→0 for enter)
- Status pulse: Tailwind `animate-pulse` for the header indicator dot

---

## 8. Scrollbar

Custom webkit scrollbar defined in `index.css`:
- Width: 6px
- Track: transparent
- Thumb: `rgba(0,0,0,0.12)`, radius 4px
- Applied via class `.custom-scrollbar`

---

## 9. New Component Checklist

When adding a new component, verify:
- [ ] `rounded-none` on all containers, inputs, buttons
- [ ] All labels are `font-mono uppercase tracking-widest`
- [ ] Interactive states use `#ff4d00` (focus ring, active border, active text)
- [ ] Borders use `stone-200` (default) or `stone-100` (subtle)
- [ ] Hover states use `stone-50` background or `stone-950` text
- [ ] No inline color values outside the defined token set
- [ ] Descriptive prose text uses `font-serif italic` (Lora)
- [ ] Icons are Material Symbols Outlined with `select-none`

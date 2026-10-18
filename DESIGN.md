# PQC-Secure Design System Specification (`DESIGN.md`)

> **Standard**: Conforms to the [`awesome-design-md`](https://github.com/voltagent/awesome-design-md) specification.  
> **Aesthetic Archetype**: **Linear Dark** with **Quantum Security Semantic Hierarchy**.  
> **Domain**: Enterprise Post-Quantum Cryptographic File Sharing, Key Lifecycle & Audit Platform.

---

## 1. Design Philosophy & Identity

PQC-Secure is an enterprise-grade post-quantum cryptography platform implementing NIST FIPS 203 (ML-KEM-768), NIST FIPS 204 (ML-DSA-65), and AES-256-GCM. In cryptography and zero-trust security, **visual trust, mathematical precision, and rapid comprehensibility** are critical. The interface must feel like an expertly crafted, high-precision security terminal rather than a generic marketing SaaS.

### Core Tenets
1. **Mathematical Craft & Precision**: Every line, border, and badge communicates structural integrity. Ultra-thin 1px hairline borders and deep obsidian surfaces evoke hardware-grade security.
2. **Zero-Distraction Density**: Security engineers, cryptographic officers, and sysadmins need high information density. Data tables, key hashes, and latency metrics are prioritized with tight, legible spacing.
3. **Cryptographic Transparency**: Security states (Quantum-Safe vs Classical, Valid vs Tampered, Active vs Revoked) are unmistakable at a glance through distinct luminescence and semantic glows.
4. **Tactile Micro-Interactions**: Actions like key generation, client-side encryption, and lattice verification produce snappy, deterministic feedback with sub-200ms transitions and subtle ambient glows.

---

## 2. Color Palette & Semantic Tokens

The color architecture is built upon a deep obsidian foundation, accented by Linear Indigo for navigation/primary interactions, and illuminated by cryptographic status colors.

### 2.1 Neutral Foundation (Obsidian Canvas)
```css
--bg-canvas:       #08090a; /* Pure deep background */
--bg-surface-0:    #0c0d0e; /* Subtle backdrop panel */
--bg-surface-1:    #111214; /* Default card, panel & table row */
--bg-surface-2:    #17191c; /* Elevated cards, hover rows, inputs */
--bg-surface-3:    #1f2126; /* Modals, popovers, active controls */
--bg-surface-subtle: rgba(255, 255, 255, 0.03);

--border-subtle:   rgba(255, 255, 255, 0.07); /* Default hairline border */
--border-default:  rgba(255, 255, 255, 0.12); /* Interactive container border */
--border-strong:   rgba(255, 255, 255, 0.22); /* Active / focused border */
--border-glow:     rgba(94, 106, 210, 0.40);  /* Primary interactive glow */
```

### 2.2 Text & Content Hierarchy
```css
--text-primary:    #f7f8f8; /* Headings, primary values, active states (100%) */
--text-secondary:  #a1a5ad; /* Body text, descriptions, table labels (70%) */
--text-tertiary:   #656a73; /* Timestamps, subtle metadata, placeholders (45%) */
--text-code:       #7dd3fc; /* Monospace hash/key highlight */
--text-inverse:    #08090a; /* Text on bright accent badges */
```

### 2.3 Cryptographic Semantic Roles
```css
/* 🛡️ Quantum-Safe / Verified / Active (ML-KEM / ML-DSA) */
--quantum-emerald:       #10b981;
--quantum-emerald-glow:  rgba(16, 185, 129, 0.18);
--quantum-emerald-border: rgba(16, 185, 129, 0.35);
--quantum-cyan:          #06b6d4;
--quantum-cyan-glow:     rgba(6, 182, 212, 0.18);

/* ⚡ Primary Brand / Navigation / Action (Linear Indigo) */
--primary-indigo:        #5e6ad2;
--primary-indigo-hover:  #6f7be8;
--primary-indigo-glow:   rgba(94, 106, 210, 0.25);
--primary-indigo-subtle: rgba(94, 106, 210, 0.12);

/* ⚠️ Classical Fallback / Transitional / Expiring (RSA/ECC) */
--warning-amber:         #f59e0b;
--warning-amber-glow:    rgba(245, 158, 11, 0.16);
--warning-amber-border:  rgba(245, 158, 11, 0.35);

/* 🚨 Revoked / Compromised / Cryptographic Tamper Alert */
--danger-rose:           #f43f5e;
--danger-rose-glow:      rgba(244, 63, 94, 0.20);
--danger-rose-border:    rgba(244, 63, 94, 0.35);

/* ℹ️ Informational / Cipher Telemetry */
--info-sky:              #38bdf8;
--info-sky-glow:         rgba(56, 189, 248, 0.15);
```

---

## 3. Typography & Monospace Precision

Typefaces must provide crisp rendering at small sizes (11px–13px) for complex tables and absolute distinction between alphanumeric characters (`0` vs `O`, `1` vs `l`) in cryptographic keys.

### 3.1 Font Families
* **Interface Body & UI**: `'Inter', 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
* **Cryptographic Data & Code**: `'JetBrains Mono', 'Geist Mono', 'SF Mono', ui-monospace, Menlo, Consolas, monospace`

### 3.2 Type Scale
| Token | Size | Line Height | Weight | Tracking | Primary Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--font-2xs` | 10px | 14px | 600 | `+0.05em` | Micro-badges, algorithm tags (UPPERCASE) |
| `--font-xs` | 11px | 16px | 500 / 600 | `+0.02em` | Table headers, metadata, key fingerprints |
| `--font-sm` | 13px | 18px | 400 / 500 | `0` | Form labels, table cells, secondary descriptions |
| `--font-base`| 14px | 20px | 400 / 500 | `0` | Standard body copy, button text, list items |
| `--font-md` | 16px | 24px | 500 / 600 | `-0.01em` | Section headers, card titles |
| `--font-lg` | 18px | 26px | 600 | `-0.02em` | Modal titles, stat highlights |
| `--font-xl` | 24px | 32px | 600 | `-0.025em`| Dashboard page headers |
| `--font-display`| 32px | 38px | 700 | `-0.03em` | Primary hero / metric counters |

### 3.3 Monospace Cryptographic Formatting
* All key IDs, SHA-256 / SHA-3 hashes, ML-KEM encapsulation ciphertexts, and digital signatures must use `font-family: var(--font-mono)`.
* Truncated hashes (e.g., `0x3a4f...e9b1`) must offer click-to-copy with a visual confirmation tooltip.
* Numeric columns in latency benchmarks must use `font-variant-numeric: tabular-nums` to prevent layout jittering during real-time updates.

---

## 4. Elevation, Depth & Surfaces

Linear's aesthetic relies on **ambient light layered upon darkness**, not heavy solid shadows.

```
Layer 3: Modals / Floating Menus / Tooltips (Z: 1000)
         └─ Background: #1f2126 + Backdrop blur (16px)
         └─ Border: rgba(255, 255, 255, 0.16)
         └─ Shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.8)

Layer 2: Cards / Expanded Rows / Elevated Panels (Z: 10)
         └─ Background: #17191c
         └─ Border: rgba(255, 255, 255, 0.10)
         └─ Shadow: 0 4px 12px rgba(0, 0, 0, 0.3)

Layer 1: Static Tables / Sidebars / Content Cards (Z: 1)
         └─ Background: #111214
         └─ Border: rgba(255, 255, 255, 0.07)

Layer 0: Canvas Base (Z: 0)
         └─ Background: #08090a (Solid Obsidian)
```

### Ambient Gradient Accents
* Top-edge glow for active cards:
  ```css
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 100%), #111214;
  ```
* Quantum-Safe Active Card Glow:
  ```css
  box-shadow: 0 0 0 1px var(--quantum-emerald-border), 0 8px 24px -6px var(--quantum-emerald-glow);
  ```

---

## 5. Layout, Spacing & Density

A disciplined 4px / 8px incremental scale ensures alignment across complex dashboards.

### 5.1 Spacing Scale
* `--space-1`: `4px`
* `--space-2`: `8px`
* `--space-3`: `12px`
* `--space-4`: `16px`
* `--space-5`: `20px`
* `--space-6`: `24px`
* `--space-8`: `32px`
* `--space-12`: `48px`

### 5.2 Application Shell Dimensions
* **Top Navigation Bar**: Fixed `52px` height, border-bottom `1px solid var(--border-subtle)`, sticky with `backdrop-filter: blur(12px)`.
* **Sidebar**: `230px` width (desktop), collapsible to `56px` (icons only).
* **Main Content Area**: Centered container `max-width: 1400px` with `padding: 24px 32px`.
* **Corner Radii**:
  * `--radius-sm`: `4px` (Inputs, inline code, micro-tags)
  * `--radius-md`: `6px` (Buttons, table rows, badges)
  * `--radius-lg`: `10px` (Cards, panels, modal dialogs)
  * `--radius-full`: `9999px` (Pills, avatar circles, status dots)

---

## 6. Component Specifications

### 6.1 Buttons
Buttons must feature a subtle inner bevel border and smooth state transitions.

* **Primary Button (Quantum / Action)**:
  * Background: `linear-gradient(180deg, #6366f1 0%, #4f46e5 100%)`
  * Color: `#ffffff`
  * Border: `1px solid rgba(255, 255, 255, 0.16)`
  * Shadow: `0 1px 2px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)`
  * Hover: `brightness(1.08)`, box-shadow includes subtle indigo glow `0 0 16px -2px rgba(99, 102, 241, 0.5)`
* **Secondary / Surface Button**:
  * Background: `var(--bg-surface-2)`
  * Color: `var(--text-primary)`
  * Border: `1px solid var(--border-default)`
  * Hover: Background `var(--bg-surface-3)`, border `var(--border-strong)`
* **Danger Button**:
  * Background: `rgba(244, 63, 94, 0.10)`
  * Color: `#f43f5e`
  * Border: `1px solid var(--danger-rose-border)`
  * Hover: Background `rgba(244, 63, 94, 0.20)`

### 6.2 Status Badges & Cryptographic Algorithm Pills
Pill-shaped badges (`border-radius: 9999px`) with 10px uppercase tracking:

* **Quantum-Safe ML-KEM-768 / ML-DSA-65**:
  * Background: `rgba(16, 185, 129, 0.12)`
  * Text: `#10b981`
  * Border: `1px solid rgba(16, 185, 129, 0.30)`
  * Indicator: 6px pulsing green dot (`animation: pulse-glow 2s infinite`)
* **AES-256-GCM Payload Encrypted**:
  * Background: `rgba(6, 182, 212, 0.12)`
  * Text: `#06b6d4`
  * Border: `1px solid rgba(6, 182, 212, 0.30)`
* **Classical Transitional (RSA/ECC)**:
  * Background: `rgba(245, 158, 11, 0.12)`
  * Text: `#f59e0b`
  * Border: `1px solid rgba(245, 158, 11, 0.30)`
* **Revoked / Inactive Key**:
  * Background: `rgba(244, 63, 94, 0.12)`
  * Text: `#f43f5e`
  * Border: `1px solid rgba(244, 63, 94, 0.30)`

### 6.3 Drag-and-Drop Cryptographic Upload Zone
* Default: Border `1px dashed var(--border-strong)`, background `var(--bg-surface-subtle)`.
* Drag Hover: Border `1px dashed var(--primary-indigo)`, background `var(--primary-indigo-subtle)`, ambient glow.
* Progress Bar: 4px height, background `linear-gradient(90deg, #10b981, #06b6d4)`, smooth ease-out progress.

### 6.4 Data Tables & Audit Logs
* Header: Background `var(--bg-surface-0)`, font size `11px`, text-transform `uppercase`, letter-spacing `0.05em`.
* Row: Height `44px`, border-bottom `1px solid var(--border-subtle)`.
* Row Hover: Background `var(--bg-surface-2)`, transition `background 120ms ease`.
* Cell Content: Truncated monospace hashes with hover popover showing full fingerprint and copy button.

### 6.5 Modals & Dialogs
* Backdrop: `rgba(0, 0, 0, 0.75)` with `backdrop-filter: blur(8px)`.
* Container: `max-width: 540px`, background `var(--bg-surface-2)`, border `1px solid var(--border-strong)`.
* Top accent line: 1px subtle gradient line spanning the modal header.

---

## 7. Motion & Micro-Interactions

Transitions follow Linear's snappy, physical response curves:

```css
--ease-out:   cubic-bezier(0.16, 1, 0.3, 1); /* Rapid start, smooth settling */
--ease-in:    cubic-bezier(0.7, 0, 0.84, 0);
--duration-fast:   120ms;
--duration-normal: 200ms;
--duration-smooth: 320ms;
```

### Motion Patterns
1. **Interactive Element Scale**: Buttons and interactive pills scale slightly on press:
   ```css
   button:active { transform: scale(0.985); }
   ```
2. **Card Hover Lift**:
   ```css
   .pqc-card:hover {
     border-color: var(--border-strong);
     transform: translateY(-1px);
     transition: transform var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
   }
   ```
3. **Pulsing Quantum Indicator**:
   ```css
   @keyframes pulse-quantum {
     0%, 100% { opacity: 1; transform: scale(1); }
     50% { opacity: 0.45; transform: scale(0.92); }
   }
   ```

---

## 8. Accessibility & Ergonomics (a11y)

* **Contrast**: All text tokens exceed WCAG 2.1 AA standards (minimum 4.5:1 ratio against surface background; primary headings exceed 14:1).
* **Keyboard Focus**: Focus rings never rely on default browser outlines:
  ```css
  :focus-visible {
    outline: 2px solid var(--primary-indigo);
    outline-offset: 2px;
  }
  ```
* **Reduced Motion**: Respect user OS motion preferences:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```

---

## 9. Production CSS Variable Master Sheet

```css
:root {
  /* Canvas & Surfaces */
  --pqc-bg-canvas: #08090a;
  --pqc-bg-surface-0: #0c0d0e;
  --pqc-bg-surface-1: #111214;
  --pqc-bg-surface-2: #17191c;
  --pqc-bg-surface-3: #1f2126;

  /* Borders */
  --pqc-border-subtle: rgba(255, 255, 255, 0.07);
  --pqc-border-default: rgba(255, 255, 255, 0.12);
  --pqc-border-strong: rgba(255, 255, 255, 0.22);

  /* Typography */
  --pqc-text-primary: #f7f8f8;
  --pqc-text-secondary: #a1a5ad;
  --pqc-text-tertiary: #656a73;
  --pqc-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --pqc-font-mono: 'JetBrains Mono', 'Geist Mono', 'SF Mono', Consolas, monospace;

  /* Cryptographic Roles */
  --pqc-quantum-green: #10b981;
  --pqc-quantum-cyan: #06b6d4;
  --pqc-accent-indigo: #5e6ad2;
  --pqc-warning-amber: #f59e0b;
  --pqc-danger-rose: #f43f5e;

  /* Radii */
  --pqc-radius-sm: 4px;
  --pqc-radius-md: 6px;
  --pqc-radius-lg: 10px;
  --pqc-radius-full: 9999px;

  /* Shadows */
  --pqc-shadow-card: 0 1px 3px rgba(0, 0, 0, 0.3), 0 4px 12px rgba(0, 0, 0, 0.15);
  --pqc-shadow-modal: 0 20px 48px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px var(--pqc-border-strong);
}
```

---

*This document serves as the authoritative source of design truth for all frontend interfaces, components, and interactive flows across the PQC-Secure application.*

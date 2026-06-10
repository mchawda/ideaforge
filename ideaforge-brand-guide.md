# IdeaForge — Brand Guide
## For Cursor, v0, and all UI development

> Use this file as your design system reference. When building any IdeaForge UI,
> follow these rules exactly. Do not introduce colors, fonts, or patterns outside this guide.

---

## 1. Brand Essence

**Name:** IdeaForge  
**Tagline:** From idea to live product in minutes.  
**Pitch line:** Browse on IdeaBrowser. Build on IdeaForge.

**Personality:** Decisive · Fast · Trustworthy · Autonomous · Bold  
**Voice:** The agent acts — it does not narrate. Every output is a statement, not a suggestion.  
**Tone:** Direct, confident, minimal. Never flowery. Never over-explain.

---

## 2. Logo & Wordmark

The wordmark is always written as one word: **ideaForge** (when rendered in code/text) or typographically as:

```
idea  (weight 400, lowercase, color: #F97316)
Forge (weight 500, sentence case, color: white or #F8FAFC)
●     (small 8px orange dot spark after the wordmark)
```

**Rules:**
- Never use the wordmark on a light background in production UI (dark theme only)
- Never separate "idea" from "Forge" onto different lines
- Minimum size: 20px combined
- The orange dot (spark) is optional in very small sizes

```html
<!-- HTML wordmark -->
<span class="wordmark">
  <span style="font-weight:400;color:#F97316;">idea</span><span style="font-weight:500;color:#F8FAFC;">Forge</span><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#F97316;margin-left:3px;margin-bottom:2px;vertical-align:baseline;"></span>
</span>
```

---

## 3. Color System

### Primary Palette

| Token | Name | Hex | Usage |
|---|---|---|---|
| `--color-forge` | Forge Fire | `#F97316` | Primary CTA, buttons, active states, key highlights |
| `--color-forge-light` | Forge Light | `#FB923C` | Hover states, secondary accents |
| `--color-forge-dim` | Forge Dim | `#3D2800` | Orange badge backgrounds, subtle highlights |
| `--color-idea` | Idea Violet | `#A78BFA` | Research agent, strategy phase, creative states |
| `--color-idea-dim` | Idea Dim | `#2D1F4E` | Violet badge backgrounds |
| `--color-live` | Live Teal | `#2DD4BF` | Deployed/success state, live indicators |
| `--color-live-dim` | Live Dim | `#0D4A3A` | Teal badge backgrounds |

### Background & Surface

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#0A0A0F` | Page background |
| `--bg-surface` | `#111117` | Card surfaces, panels |
| `--bg-elevated` | `#1A1A28` | Elevated cards, dropdowns, modals |
| `--bg-border` | `#2D2D3A` | All borders and dividers |

### Text

| Token | Hex | Usage |
|---|---|---|
| `--text-primary` | `#F8FAFC` | Headlines, primary body text |
| `--text-secondary` | `#94A3B8` | Subtitles, metadata, labels |
| `--text-muted` | `#475569` | Placeholders, disabled states |

### Tailwind Mappings (for v0)

```
Forge Fire     → orange-500  (#F97316)
Forge Light    → orange-400  (#FB923C)
Idea Violet    → violet-400  (#A78BFA)
Live Teal      → teal-400    (#2DD4BF)
Background     → slate-950 / custom #0A0A0F
Surface        → slate-900 / custom #111117
Elevated       → slate-800 / custom #1A1A28
Border         → slate-700 / custom #2D2D3A
Text Primary   → slate-50   (#F8FAFC)
Text Secondary → slate-400  (#94A3B8)
```

### CSS Variables (add to :root or globals.css)

```css
:root {
  --color-forge: #F97316;
  --color-forge-light: #FB923C;
  --color-forge-dim: #3D2800;
  --color-idea: #A78BFA;
  --color-idea-dim: #2D1F4E;
  --color-live: #2DD4BF;
  --color-live-dim: #0D4A3A;
  --bg-base: #0A0A0F;
  --bg-surface: #111117;
  --bg-elevated: #1A1A28;
  --bg-border: #2D2D3A;
  --text-primary: #F8FAFC;
  --text-secondary: #94A3B8;
  --text-muted: #475569;
}
```

---

## 4. Typography

**Font family:** Inter (Google Fonts)  
**Fallback:** -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 400;
  color: var(--text-primary);
  background: var(--bg-base);
}
```

### Type Scale

| Role | Size | Weight | Color |
|---|---|---|---|
| Display / Hero | 48–64px | 500 | `#F8FAFC` |
| H1 | 36px | 500 | `#F8FAFC` |
| H2 | 24px | 500 | `#F8FAFC` |
| H3 | 18px | 500 | `#F8FAFC` |
| Body | 15–16px | 400 | `#F8FAFC` |
| Small / Label | 13px | 400 | `#94A3B8` |
| Micro / Meta | 11px | 500 | `#94A3B8` (uppercase + tracking) |

**Rules:**
- Two weights only: 400 (regular) and 500 (medium). Never 600, 700, or bold.
- Sentence case always. Never ALL CAPS except micro labels (11px).
- Letter spacing: normal for body; `0.08em` for micro uppercase labels only.
- Line height: `1.6` for body, `1.2` for headings.

---

## 5. Spacing & Layout

```
Base unit: 4px
Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96px

Border radius:
  Small (inputs, badges): 6px
  Medium (buttons, cards): 8px
  Large (panels, modals): 12px
  Full (pills, avatars): 9999px

Border: 0.5px solid #2D2D3A (always 0.5px — never 1px)

Max content width: 1200px
Content padding (mobile): 16px
Content padding (desktop): 48px
```

---

## 6. Components

### Buttons

```html
<!-- Primary (Forge Fire) -->
<button style="
  background: #F97316;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 15px;
  font-weight: 500;
  font-family: Inter, sans-serif;
  cursor: pointer;
  transition: background 0.15s;
">Build This →</button>

<!-- Ghost -->
<button style="
  background: transparent;
  color: #F8FAFC;
  border: 0.5px solid #2D2D3A;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 15px;
  font-weight: 500;
  font-family: Inter, sans-serif;
  cursor: pointer;
">Browse Ideas</button>

<!-- Destructive / Secondary -->
<button style="
  background: #1A1A28;
  color: #94A3B8;
  border: 0.5px solid #2D2D3A;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 15px;
">Cancel</button>
```

### Status Badges

```html
<!-- Live (deployed) -->
<span style="background:#0D4A3A;color:#2DD4BF;font-size:11px;font-weight:500;padding:3px 10px;border-radius:9999px;display:inline-flex;align-items:center;gap:5px;">
  <span style="width:6px;height:6px;border-radius:50%;background:#2DD4BF;"></span>
  Live
</span>

<!-- Building -->
<span style="background:#3D2800;color:#F97316;font-size:11px;font-weight:500;padding:3px 10px;border-radius:9999px;">
  Building...
</span>

<!-- Researching -->
<span style="background:#2D1F4E;color:#A78BFA;font-size:11px;font-weight:500;padding:3px 10px;border-radius:9999px;">
  Researching
</span>
```

### Cards

```html
<div style="
  background: #111117;
  border: 0.5px solid #2D2D3A;
  border-radius: 12px;
  padding: 20px 24px;
">
  <!-- card content -->
</div>
```

### Input Fields

```html
<input type="text" placeholder="Paste IdeaBrowser URL..." style="
  background: #1A1A28;
  border: 0.5px solid #2D2D3A;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 15px;
  color: #F8FAFC;
  font-family: Inter, sans-serif;
  width: 100%;
  outline: none;
  transition: border-color 0.15s;
">
<!-- On focus: border-color: #F97316 -->
```

### Agent Progress Tracker

Three states per step: pending (gray) → active (orange, pulsing) → done (teal)

```html
<div style="display:flex;flex-direction:column;gap:0;">
  <!-- Done step -->
  <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:0.5px solid #2D2D3A;">
    <div style="width:8px;height:8px;border-radius:50%;background:#2DD4BF;flex-shrink:0;"></div>
    <span style="font-size:14px;color:#F8FAFC;">Research</span>
    <span style="font-size:12px;color:#2DD4BF;margin-left:auto;">Done</span>
  </div>
  <!-- Active step -->
  <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:0.5px solid #2D2D3A;">
    <div style="width:8px;height:8px;border-radius:50%;background:#F97316;flex-shrink:0;animation:pulse 1s infinite;"></div>
    <span style="font-size:14px;color:#F97316;">Building UI</span>
    <span style="font-size:12px;color:#F97316;margin-left:auto;">●●●</span>
  </div>
  <!-- Pending step -->
  <div style="display:flex;align-items:center;gap:12px;padding:10px 0;">
    <div style="width:8px;height:8px;border-radius:50%;background:#2D2D3A;flex-shrink:0;"></div>
    <span style="font-size:14px;color:#475569;">Deploy AWS</span>
  </div>
</div>
<style>
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
</style>
```

---

## 7. Agent Phase Color Mapping

Each agent phase has a consistent color so users always know what's happening:

| Phase | Color | Hex |
|---|---|---|
| Research (Exa) | Idea Violet | `#A78BFA` |
| Strategy | Idea Violet | `#A78BFA` |
| Human checkpoint | Forge Fire | `#F97316` |
| Building UI (v0) | Forge Fire | `#F97316` |
| Deploying AWS | Forge Fire | `#F97316` |
| Stripe setup | Forge Fire | `#F97316` |
| Complete / Live | Live Teal | `#2DD4BF` |
| Error | Red | `#F87171` |

---

## 8. Voice & Copy Rules

**Do:**
- "Your product is live."
- "Chose $19/mo — undercuts Notion by 40%."
- "3 competitors found. Gap identified."
- "Deployed to AWS. Stack: Lambda + DynamoDB."
- "Build this →"

**Don't:**
- "Your product has been successfully deployed!"
- "We considered several pricing options and determined..."
- "Please wait while we process your request..."
- "Great choice! Here's what we found:"

**Rules:**
- Statements over sentences where possible
- Numbers beat adjectives ("undercuts by 40%" not "significantly cheaper")
- Agent messages are factual, not enthusiastic
- CTAs use arrow: "Build this →" not "Click here to build"
- Error messages explain what happened + what to do: "Stripe API failed. Retrying..." not "An error occurred."

---

## 9. v0 Prompt Template

Use this prompt when generating any IdeaForge UI with Vercel v0:

```
Build a dark-theme React/Next.js UI for IdeaForge, an AI agent that turns ideas into live SaaS products.

Design system:
- Background: #0A0A0F
- Surface cards: #111117, border 0.5px solid #2D2D3A, border-radius 12px
- Elevated elements: #1A1A28
- Primary accent: #F97316 (Forge Fire orange) — for CTAs, active states
- Idea color: #A78BFA (violet) — for research/strategy phases  
- Live color: #2DD4BF (teal) — for deployed/success states
- Text primary: #F8FAFC, Text secondary: #94A3B8, Text muted: #475569
- Font: Inter 400/500 only. No bold/semibold.
- Borders: always 0.5px, never 1px.

Wordmark: "idea" in weight 400 orange (#F97316) + "Forge" in weight 500 white, followed by a small orange dot.

[DESCRIBE THE SPECIFIC COMPONENT OR PAGE HERE]

Requirements:
- Tailwind CSS with shadcn/ui components
- Dark mode only (no light mode toggle needed)
- Clean, minimal, no decorative gradients or glows
- Status indicators use: violet = researching, orange = building, teal = live
- All buttons use rounded-lg, primary buttons use bg-orange-500 hover:bg-orange-400
- Export as a single Next.js page/component
```

---

## 10. Cursor Instructions

Add this to your `.cursorrules` or `CLAUDE.md` in the project root:

```
# IdeaForge UI Rules

This is a dark-theme SaaS product. Follow these rules for ALL UI work:

## Colors (never deviate)
- Page bg: #0A0A0F
- Card surface: #111117  
- Elevated: #1A1A28
- Borders: 0.5px solid #2D2D3A
- Primary CTA: #F97316 (orange)
- Research/idea state: #A78BFA (violet)
- Live/success state: #2DD4BF (teal)
- Error: #F87171
- Text: #F8FAFC (primary), #94A3B8 (secondary), #475569 (muted)

## Typography
- Font: Inter only
- Weights: 400 and 500 ONLY. Never 600, 700, bold.
- Sentence case always.

## Components
- Borders: 0.5px solid #2D2D3A — never 1px
- Border radius: 8px (buttons/inputs), 12px (cards/panels)
- Buttons: rounded-lg, no uppercase
- Agent status dots: 8px circle, gray=pending, orange=active, teal=done

## Voice
- Statements not sentences. "Product is live." not "Your product has been successfully deployed."
- Numbers beat adjectives.
- No exclamation marks in agent outputs.
```

---

## 11. Presentation Theme

**Slide background:** `#0A0A0F`  
**Accent color:** `#F97316`  
**Heading font:** Inter 500  
**Body font:** Inter 400  
**Slide width:** 16:9 widescreen

**Slide rules:**
- Max 20 words of text per slide (visuals carry the weight)
- One idea per slide
- Use the orange dot (●) as a bullet point instead of default bullets
- Highlight key numbers in `#F97316`
- Use teal (`#2DD4BF`) to show "live" or "success" outcomes
- Demo screenshots go on dark card surfaces (`#111117` with 12px radius)

---

## 12. UX Reference — Aura

Use [Aura](https://www.aura.build/) in two distinct ways:

### A) IdeaForge operator UI (`apps/web`)
Layout and interaction patterns only — hero command bar, grid background, section headers. Map to IdeaForge tokens (sections 3–6). Never use Aura colors on the operator dashboard.

### B) Generated product UI (each idea → live product)
Aura is the **design portfolio**. Each build picks a template direction from `config/aura_portfolio.json` so every product looks unique.

**Flow:**
1. Strategy agent matches niche → Aura template (e.g. Lumina AI, Verdant SaaS, Nexura Agency)
2. Builder agent injects that style into the v0 prompt
3. v0 generates the customer landing page — distinct palette, layout, typography per idea

**Rules for generated products:**
- Unique visual identity per product (not IdeaForge orange/violet/teal unless the niche fits)
- Remix Aura template *direction* — mood, layout, typography — not a pixel copy
- IdeaForge brand colors apply only to the operator UI, not customer products

**Do not borrow on operator UI:**
- Aura light theme, fonts, or accent colors
- Decorative gradients beyond subtle grid/depth

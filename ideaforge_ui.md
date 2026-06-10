# IdeaForge — UI Build Prompt
## Paste this into v0, Cursor, or any AI coding tool to generate the full UI

---

## MASTER v0 PROMPT — Full Application

Paste this entire block into v0 to generate the complete IdeaForge UI in one shot:

```
Build a complete dark-theme Next.js 14 application for IdeaForge — an AI agent that 
autonomously turns business ideas into live, deployed SaaS products.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Colors:
  Page background:     #0A0A0F
  Card surface:        #111117
  Elevated elements:   #1A1A28
  Border:              #2D2D3A (0.5px, never 1px)
  Primary/CTA:         #F97316 (orange — "Forge Fire")
  Research phase:      #A78BFA (violet — "Idea Violet")
  Deployed/success:    #2DD4BF (teal — "Live Teal")
  Error:               #F87171
  Text primary:        #F8FAFC
  Text secondary:      #94A3B8
  Text muted:          #475569

Typography:
  Font: Inter (Google Fonts), weights 400 and 500 ONLY
  Never use 600, 700, or bold. Never ALL CAPS except 11px micro labels.
  Sentence case always.

Layout:
  Max width: 1200px centered
  Border radius: 8px inputs/buttons, 12px cards/panels
  Spacing scale: 4/8/12/16/24/32/48/64px

Wordmark:
  <span style="font-weight:400;color:#F97316">idea</span>
  <span style="font-weight:500;color:#F8FAFC">Forge</span>
  + small 7px orange circle dot after

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Build these 3 pages as separate route files:

━━━ PAGE 1: Landing Page (/) ━━━

Navigation bar (sticky, bg #0A0A0F, border-bottom 0.5px #2D2D3A):
  - Left: wordmark "ideaForge●"
  - Right: "Sign in" ghost button + "Get started" orange button

Hero section (centered, padding 120px top):
  - Eyebrow: small orange pill badge — "● Powered by Exa · AWS · Vercel · Stripe"
  - H1 (56px, weight 500): "Browse on IdeaBrowser."
    Second line with orange text: "Build on IdeaForge."
  - Subheadline (18px, #94A3B8): "Paste a validated business idea. Get a live, deployed, 
    monetised SaaS product in minutes — no code required."
  - Input row (max-width 640px, centered):
    [ IdeaBrowser URL input (left, flex-1) ][ "Build This →" orange button ]
    Placeholder: "https://ideabrowser.com/ideas/..."
    Below input: small text — "Or describe your own idea →"
  - Social proof: "Trusted by builders at" + 3 company logo placeholders

How it works section (padding 96px):
  - Section label: "The pipeline" (11px, uppercase, orange, tracked)
  - H2: "From idea to live product"
  - 6-step horizontal pipeline with connecting arrows:
    1. [Violet] Import — "Paste IdeaBrowser URL or describe your domain"
    2. [Violet] Research — "Exa searches competitors, pricing, pain points"
    3. [Violet] Strategy — "Agent decides niche, ICP, features, pricing"
    4. [Orange] You approve — "Review the strategy brief, approve or adjust"
    5. [Orange] Build & Deploy — "UI generated, AWS deployed, Stripe connected"
    6. [Teal]   Live — "Working product with Stripe checkout in ~6 min"
  Each step is a card (bg #111117, border, 12px radius) with:
    - Colored number circle (1–6)
    - Step name (15px, 500)
    - Description (13px, #94A3B8)

Features section (padding 96px, alternating left/right layout):
  Feature 1: "Research that thinks" — violet accent
    Agent runs 10+ Exa searches to find underserved niches before suggesting anything
  Feature 2: "Decisions, not options" — orange accent
    Agent commits to a specific product with sourced rationale. Not a list of ideas.
  Feature 3: "Real infrastructure" — orange accent
    AWS Lambda + DynamoDB + API Gateway deployed to your account. Not a mock.
  Feature 4: "Ready to charge" — teal accent
    Stripe product, pricing tiers, and checkout link created automatically.

Decision Brief preview (padding 96px, bg #111117 section):
  - H2: "Every decision, explained"
  - Show a mockup card of the Decision Brief output with:
    - Product name, niche, ICP
    - Pricing rationale with competitor benchmarks
    - Sources cited
    - "View full brief →" link in orange

CTA section (padding 96px, centered):
  - H2: "Your next product is one URL away."
  - Same input row as hero
  - Fine print: "Free to try. AWS + Vercel account required for deployment."

Footer (border-top 0.5px #2D2D3A, padding 48px):
  - Left: wordmark + tagline "From idea to live product in minutes."
  - Right: Links — Docs, GitHub, IdeaBrowser (external), Twitter

━━━ PAGE 2: App / Builder (/app) ━━━

Split layout (sidebar + main):

Left sidebar (280px, bg #111117, border-right 0.5px #2D2D3A):
  - Wordmark at top
  - "New build" orange button
  - List of past builds (product name + status badge each)
  - Bottom: user avatar + email

Main content area:

STATE 1 — Empty (no active build):
  Centered empty state:
    Orange spark icon (large, 64px)
    H2: "What are you building today?"
    Two input options stacked:
      Option A card: "Import from IdeaBrowser"
        URL input with "Import idea" button
      Option B card: "Describe your own idea"  
        Textarea with "Start building →" button

STATE 2 — Building (agent running):
  Top: Product name being built + "Building..." badge (orange)
  Agent progress panel (bg #111117, 12px radius):
    6 steps as vertical list, each with:
      - Status dot (gray/orange pulse/teal)
      - Step name + current action description
      - Timestamp when completed
  Below progress: Live log stream (monospace, #94A3B8, 13px, scrolling)

STATE 3 — Human Checkpoint (awaiting approval):
  Modal overlay (centered card, max-width 600px):
    Header: "Review your product strategy" 
    Orange badge: "● Awaiting your approval"
    Strategy brief card showing:
      - Product name (large, orange)
      - Niche (one sentence)
      - ICP (one sentence)
      - Features (bullet list with orange dots)
      - Pricing table (tiers + prices)
      - Rationale paragraph with source citations
    Two buttons: "Approve — Build it →" (orange) + "Adjust strategy" (ghost)

STATE 4 — Complete:
  Success header: Large teal checkmark + "Your product is live"
  Result cards (2-column grid):
    - Live URL card with "Open →" button (teal)
    - Stripe dashboard card with payment link
    - AWS console link
    - Decision brief download
  "Build another →" orange CTA button

━━━ PAGE 3: Decision Brief (/brief/[id]) ━━━

Clean document layout (max-width 800px centered, padding 64px):
  - Back link "← Back to builds"
  - H1: "[Product Name] — Decision Brief"
  - Metadata row: date, session ID, agent version
  
  Sections (each with H2 + body):
    1. Executive summary
    2. Market opportunity (from research)
    3. Product decision (what was built and why)
    4. Pricing rationale (with competitor table)
    5. Technical architecture (AWS resources list)
    6. Revenue model (Stripe config)
    7. Assumptions & risks
  
  Source citations at bottom (numbered, teal links)
  "Download PDF" ghost button in top-right

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPONENT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Buttons:
  Primary: bg-[#F97316] text-white hover:bg-[#FB923C] rounded-lg px-6 py-2.5 text-[15px] font-medium
  Ghost: bg-transparent text-[#F8FAFC] border border-[#2D2D3A] hover:border-[#475569] rounded-lg px-6 py-2.5

Inputs:
  bg-[#1A1A28] border border-[#2D2D3A] rounded-lg px-4 py-3 text-[#F8FAFC] placeholder-[#475569]
  focus:outline-none focus:border-[#F97316]

Cards:
  bg-[#111117] border border-[#2D2D3A] rounded-xl p-5

Status badges (pill shape):
  Live:       bg-[#0D4A3A] text-[#2DD4BF] text-[11px] font-medium px-3 py-1 rounded-full
  Building:   bg-[#3D2800] text-[#F97316] text-[11px] font-medium px-3 py-1 rounded-full
  Researching: bg-[#2D1F4E] text-[#A78BFA] text-[11px] font-medium px-3 py-1 rounded-full

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Active agent step dot: pulse animation (opacity 1 → 0.3 → 1, 1.2s infinite)
Page transitions: fade in (opacity 0 → 1, 200ms)
Build completion: teal checkmark scales in (scale 0 → 1, 300ms, ease-out)
Log stream: new lines slide up from bottom

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECH STACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Next.js 14 App Router
- Tailwind CSS
- shadcn/ui (dark theme configured)
- TypeScript
- Use Server-Sent Events (SSE) for the live agent log stream

Export each page as its own file. Use Tailwind classes throughout.
Do not use any light mode styles. Dark only.
```

---

## COMPONENT-LEVEL v0 PROMPTS

Use these for individual components when you need to regenerate just one piece:

### Hero Input Row
```
Build a dark-theme hero input row for IdeaForge.
Background #0A0A0F. Max-width 640px centered.
Left: text input (bg #1A1A28, border 0.5px #2D2D3A, border-radius 8px, padding 12px 16px, 
  text #F8FAFC, placeholder #475569 "https://ideabrowser.com/ideas/...", 
  focus border #F97316, flex-1).
Right: "Build This →" button (bg #F97316, text white, border-radius 8px, padding 12px 24px,
  font-weight 500, hover bg #FB923C, no border).
Below row: small text (13px #94A3B8) "Or describe your own idea →" as a clickable link 
in #F97316.
```

### Agent Progress Panel
```
Build a dark-theme agent progress tracker for IdeaForge.
Card: bg #111117, border 0.5px #2D2D3A, border-radius 12px, padding 20px.
6 steps as a vertical list, dividers between each (0.5px #2D2D3A).
Each step row: 
  - 8px circle dot (gray=#2D2D3A pending, orange=#F97316 active with pulse, teal=#2DD4BF done)
  - Step name (14px #F8FAFC, or #F97316 if active, or #475569 if pending)
  - Right: "Done" in #2DD4BF if done, "●●●" pulsing in #F97316 if active
Steps: Research, Strategy, Building UI, Deploying AWS, Setting up Stripe, Complete
Show step 3 (Building UI) as active.
```

### Strategy Approval Modal
```
Build a dark-theme strategy approval modal for IdeaForge.
Modal card: bg #111117, border 0.5px #2D2D3A, border-radius 16px, padding 32px, max-width 560px.
Top: "Review your product strategy" (18px weight 500 #F8FAFC) + 
  orange badge "● Awaiting your approval" (bg #3D2800 text #F97316).
Divider (0.5px #2D2D3A).
Product name: large (28px weight 500 #F97316) — "InvoiceFlow"
Below: metadata row with 3 pills (bg #1A1A28 border #2D2D3A rounded-full text-[13px]):
  "Freelance designers" · "$19/mo Pro" · "Underprice FreshBooks"
Features list (small bullet list with orange dots):
  4 short feature items
Pricing mini-table (2 tiers: Free + Pro $19/mo)
Rationale paragraph (13px #94A3B8, 3 sentences, italic)
Sources row: 3 small blue links
Bottom button row: "Approve — Build it →" (orange, full-width) + "Adjust strategy" (ghost)
```

### Decision Brief Card
```
Build a dark-theme decision brief summary card for IdeaForge.
Card: bg #111117, border 0.5px #2D2D3A, border-radius 12px, padding 24px.
Top row: "Decision Brief" label (11px uppercase tracking #94A3B8) + 
  teal "● Live" badge + "Download PDF" ghost button right-aligned.
Product name (20px weight 500 #F8FAFC) + niche (14px #94A3B8).
3 metric cards in a row (bg #1A1A28, border-radius 8px, padding 12px):
  Market: "$2.4B" | Pricing: "$19/mo" | Competitors: "4 found"
Rationale excerpt (13px #94A3B8, 2 lines, truncated with "Read more →" in orange).
Sources: 3 small links in #A78BFA (violet).
```

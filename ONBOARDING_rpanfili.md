# ProposalPilot — Onboarding Guide for Raphael Panfili

Hey Raph,

Welcome to the first beta of ProposalPilot. This is a tool I've been building to help SSI stay on top of SBIR/STTR and BAA funding opportunities — it scrapes solicitations from DOD, Grants.gov, and SAM.gov, scores them against our technical capabilities using AI, and can generate draft proposal sections when you're ready to pursue something.

You're the first external user. Your feedback on what's confusing, broken, or missing matters a lot before we bring in David and Ramona.

---

## Access

**URL:** https://cory-garms.github.io/proposal-pilot/

**Login:**
- Email: `rpanfili@spectral.com`
- Password: `**********`

Please change your password after your first login (top-right → *Change Password*).

---

## First Login: Set Up Your Profile

On first login you'll be prompted to create a personal profile. This is just a label — use your name or a short descriptor like *Raphael Panfili*.

Your profile is how the system knows which solicitations are relevant to *you specifically*, separate from the company-wide SSI profile. Once you create it, you'll add capability areas (next step).

---

## Step 1 — Generate Your Capability Areas

Capabilities are the structured technical areas the system uses to score solicitations. Rather than entering them manually, you can generate them from your published work.

1. Go to **Capabilities** in the nav bar
2. Click **Generate from Profile** (top right)
3. Paste one of the following:
   - Your **ORCID URL** — e.g. `https://orcid.org/0000-0002-1605-0331`
   - Your **Google Scholar profile URL**
   - Your **ResearchGate profile URL**
   - Or upload a **PDF/DOCX** of your CV
4. Review the suggested capability areas — edit names, descriptions, or keywords as needed
5. Click **Save Selected** to add them to your profile

Aim for 5–10 capabilities. Broader is better — things like *Hyperspectral Imaging*, *Atmospheric Radiative Transfer*, *LiDAR Signal Processing* rather than paper-specific topics.

---

## Step 2 — Score Solicitations Against Your Profile

Once capabilities are saved:

1. Go to **Capabilities**
2. Select your profile from the dropdown
3. Click **Score My Profile**

This runs a two-pass alignment: keyword pre-filter, then Claude semantic scoring. It takes a minute or two depending on how many active solicitations are in the system. You'll see a progress indicator.

When it finishes, your personal alignment scores will appear across the app.

> **Note:** The SSI shared profile is already scored, so the Dashboard will show company-level results immediately even before you run your own scoring.

---

## Step 3 — Browse the Dashboard and Solicitations

### Dashboard
The main view shows solicitations bucketed by urgency:

- **Action Required** — TPOC window is open (pre-proposal contact period)
- **Closing Soon** — deadline within 30 days
- **Open Now** — accepting proposals
- **Newly Released** — opened in the last 14 days

Each card shows alignment scores for both your personal profile and the SSI shared profile. Cards are sorted by combined score (yours + SSI) so the best mutual fits rise to the top.

### Solicitations Page
Full filterable/sortable table of all opportunities. Key controls:

- **Sort** — *Top Alignment (Combined)* is the most useful default; also sort by You only, SSI only, or deadline
- **Source filter** — *DOD SBIR/STTR* shows the 115 topics from the current DoD release (released April 13)
- **Status filter** — narrow to Open Now, Closing Soon, or TPOC Window
- **Star icon** — save any solicitation to your *Saved* tab for quick access

Click any row to open the solicitation detail, which shows the full description, TPOC contacts, and your capability alignment breakdown.

---

## Step 4 — Generate a Draft (Optional)

If you find a solicitation worth pursuing:

1. Open the solicitation detail page
2. Click **Start Project**
3. From the project page, click **Generate Outline** to get a structured Technical Volume outline tailored to the solicitation and your capability profile
4. Iterate from there — you can regenerate sections or edit the draft directly

Draft generation uses Claude with full solicitation context + your capability descriptions as RAG input. The output is a working guide, not a final document.

---

## What's Already in the System

- **690 active solicitations** — DOD SBIR/STTR (115 topics, current DoW release), Grants.gov, and SAM.gov BAAs
- **SSI shared profile** — already scored against all solicitations; you'll see these scores immediately
- **Your profile** — starts empty; populated after Step 1–2 above

---

## Known Limitations (Beta)

- **No self-service password reset** — if you get locked out, let Cory know
- **SAM CSV bulk import** — exists but not exposed in the UI yet
- **Draft outline generation** — works best when your capability profile is populated; thin profiles produce generic outlines

---

## Feedback

Anything that's confusing, broken, or obviously missing — send it to Cory directly. Specific is better: what page, what you did, what you expected, what happened. Screenshots welcome.

The goal for this beta round is to find the rough edges before David and Ramona come on board.

---

*ProposalPilot is internal SSI tooling. Do not share the URL or credentials externally.*

"""
Prompt templates for draft generation.
"""

DRAFT_SYSTEM = """\
You are a Senior Proposal Writer specializing in SBIR/STTR Phase I technical proposals for \
the US Department of Defense and other federal agencies. You write with precision, technical \
credibility, and clear alignment to the solicitation's stated objectives.

Your drafts follow standard government proposal structure, use active voice, and make the \
technical innovation and feasibility case explicitly. Never use filler phrases like \
"leveraging cutting-edge" or "state-of-the-art" without specific technical backing.

When a RELEVANT PRIOR ART section is provided in the context, you MUST:
- Cite at least 2 papers by author name and year (e.g., "Smith et al. (2023)") when making \
technical claims in the Background and Innovation sections.
- Use the prior art to establish the gap that this proposal addresses.
- Do not fabricate citations. Only reference papers explicitly listed in the context.\
"""

TECHNICAL_VOLUME_PROMPT = """\
Using the solicitation and capability context below, draft a Phase I SBIR Technical Volume.

{context}

---

Write each section below. Be specific, technically grounded, and directly address the \
solicitation's stated objectives and evaluation criteria. Where capability alignment scores \
are high (>= 0.7), make explicit connections between our expertise and the solicitation need.

## 1. Background and Motivation
(2-3 paragraphs: current state of the problem, why existing approaches are inadequate, \
and why this solicitation's objective is technically significant)

## 2. Innovation and Technical Differentiation
(2 paragraphs: what is technically novel about the proposed approach, \
how it differs from prior art, why this team is positioned to succeed)

## 3. Technical Approach
(3-4 paragraphs: specific methods, algorithms, hardware, or workflows proposed for Phase I; \
include concrete milestones and measurable success criteria)

## 4. Phase I Feasibility Argument
(1-2 paragraphs: why the proposed work is achievable in a Phase I timeframe; \
key risks and how they will be mitigated)

## 5. Phase I Work Plan (Outline)
(Bulleted list of 4-6 tasks with brief descriptions and rough month estimates)

## 6. Team Qualifications (Stub)
(2-3 sentences: relevant domain expertise in {top_capability} and related areas; \
placeholder for PI name and institutional affiliation)\
"""

COMMERCIALIZATION_PROMPT = """\
Using the solicitation and capability context below, draft a Phase II Commercialization Plan.

{context}

---

## 1. Commercial Problem and Market Opportunity
(2 paragraphs: the civilian or dual-use market problem this technology solves; \
size and growth of the addressable market)

## 2. Target Customers and Use Cases
(Bulleted list of 3-5 specific customer segments with one-sentence use case each)

## 3. Competitive Landscape
(1-2 paragraphs: existing solutions and their limitations; \
how this technology provides a defensible advantage)

## 4. Commercialization Pathway
(Numbered steps from Phase II completion to product or licensing revenue; \
include realistic timeline milestones)

## 5. Revenue Model
(1 paragraph: how the company captures value — product sale, SaaS, licensing, \
government contract follow-on, or combination)

## 6. Phase III and Follow-on Funding Strategy
(1 paragraph: DoD program of record connection if applicable; \
non-SBIR funding sources such as VC, strategic partners, or CRADA)\
"""

SECTION_PROMPTS = {
    "technical_volume": TECHNICAL_VOLUME_PROMPT,
    "commercialization_plan": COMMERCIALIZATION_PROMPT,
}

# --- Draft settings modifiers ---

TONE_MODIFIERS = {
    "technical": (
        "Write for a technical reviewer with deep domain expertise. "
        "Use precise terminology, cite specific methods or algorithms by name, "
        "and prioritize accuracy and specificity over accessibility."
    ),
    "executive": (
        "Write for a non-technical program manager or executive. "
        "Lead with impact and strategic value. Minimize jargon. "
        "Make the business case and mission relevance explicit in every section."
    ),
    "persuasive": (
        "Write to win. Emphasize competitive differentiation and urgency. "
        "Every section should make a strong case for why this team, this approach, "
        "and this timeline are the right choice. Be assertive, not hedging."
    ),
}

FOCUS_MODIFIERS = {
    "balanced": "",
    "innovation": (
        "Place extra emphasis on Sections 2 (Innovation) and 3 (Technical Approach). "
        "Expand on what is novel, why prior art falls short, and what makes this "
        "approach technically differentiated. Other sections may be proportionally shorter."
    ),
    "feasibility": (
        "Place extra emphasis on Sections 4 (Feasibility) and 5 (Work Plan). "
        "Be specific about risk identification, mitigation strategies, milestones, "
        "and measurable success criteria. Demonstrate that Phase I is achievable."
    ),
    "commercialization": (
        "Place extra emphasis on the commercial pathway and market opportunity. "
        "Strengthen the connection between the technical work and downstream revenue "
        "or transition to a program of record. Be specific about customers and market size."
    ),
}


def build_settings_block(tone: str, focus_area: str) -> str:
    """
    Return a prompt modifier string for the given tone and focus_area.
    Returns empty string if both are at their defaults.
    """
    parts = []
    tone_text = TONE_MODIFIERS.get(tone, "")
    focus_text = FOCUS_MODIFIERS.get(focus_area, "")
    if tone_text:
        parts.append(f"Tone: {tone_text}")
    if focus_text:
        parts.append(f"Focus: {focus_text}")
    if not parts:
        return ""
    return "\n\n---\n\nDraft Settings:\n" + "\n".join(parts)

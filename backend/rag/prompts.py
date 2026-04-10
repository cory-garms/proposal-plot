"""
Prompt templates for draft generation.
"""

DRAFT_SYSTEM = """\
You are a Senior Proposal Writer specializing in SBIR/STTR Phase I technical proposals for \
the US Department of Defense and other federal agencies. You produce concise, technically \
credible proposal outlines that a PI can use as a writing guide.

Each outline section must contain:
- A one-sentence statement of purpose for that section
- 3-6 bullet points identifying the specific content to include
- Where capability alignment scores are high (>= 0.7), call out the explicit connection \
between team expertise and the solicitation need

Be specific and technical. No filler phrases. Bullets should be actionable writing prompts, \
not generic headings.\
"""

TECHNICAL_VOLUME_PROMPT = """\
Using the solicitation and capability context below, produce a structured outline for a \
Phase I SBIR Technical Volume. This is a writing guide, not a full draft.

{context}

---

## 1. Background and Motivation
- [3-5 bullets: key problem statements, gaps in current approaches, why this solicitation matters]

## 2. Innovation and Technical Differentiation
- [3-4 bullets: what is novel, how it differs from prior art, team's unique positioning in {top_capability}]

## 3. Technical Approach
- [4-6 bullets: specific methods, algorithms, hardware, or workflows; each bullet = one subsection of the final draft]

## 4. Phase I Feasibility Argument
- [3-4 bullets: why achievable in Phase I, key risks, mitigation strategies, measurable success criteria]

## 5. Phase I Work Plan
- [4-6 tasks with rough month ranges, e.g. "Task 1 (M1-M3): ..."]

## 6. Team Qualifications
- [2-3 bullets: relevant expertise in {top_capability} and adjacent areas; flag where specific credentials or publications should be cited]\
"""

COMMERCIALIZATION_PROMPT = """\
Using the solicitation and capability context below, produce a structured outline for a \
Phase II Commercialization Plan. This is a writing guide, not a full draft.

{context}

---

## 1. Commercial Problem and Market Opportunity
- [3-4 bullets: market problem, addressable market size, growth drivers]

## 2. Target Customers and Use Cases
- [3-5 bullets: one customer segment per bullet with specific use case]

## 3. Competitive Landscape
- [3-4 bullets: named competing solutions, their limitations, our differentiation]

## 4. Commercialization Pathway
- [4-6 bullets: ordered steps from Phase II completion to revenue or transition]

## 5. Revenue Model
- [2-3 bullets: value capture mechanism, pricing model, expected Phase III contract or licensing path]

## 6. Phase III and Follow-on Funding
- [2-3 bullets: DoD program of record connections, non-SBIR funding sources to pursue]\
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

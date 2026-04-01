"""
Prompt templates for capability alignment scoring.
"""

ALIGNMENT_SYSTEM = """\
You are a technical proposal analyst evaluating whether a government SBIR/STTR solicitation \
topic is a strong match for a specific technical capability.

You must respond with valid JSON only. No markdown, no prose outside the JSON object.\
"""

ALIGNMENT_USER = """\
Capability: {capability_name}
Capability description: {capability_description}

Solicitation title: {title}
Solicitation agency: {agency}
Solicitation description:
{description}

Score how well this solicitation matches the capability on a scale from 0.0 to 1.0:
- 1.0 = the solicitation directly requires this capability as its core technical focus
- 0.7 = the capability is highly relevant and would give a strong competitive advantage
- 0.4 = the capability is tangentially relevant or applicable to part of the work
- 0.1 = the capability is barely relevant
- 0.0 = no meaningful connection

Respond with this exact JSON structure:
{{
  "score": <float 0.0-1.0>,
  "rationale": "<one sentence explaining the score, max 25 words>"
}}\
"""

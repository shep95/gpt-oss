"""
gpt_oss.brain — a Brain Orchestrator that wires the cognitive-region doctrines
together so the model routes through the right "brains" per request, the way a
human brain recruits only the regions a task needs.

Public API:
    from gpt_oss.brain import compose, route, explain
    system_prompt = compose(user_text, has_image=False, base_instructions=None)
"""

from .orchestrator import (
    BRAINS,
    BrainDecision,
    BrainSpec,
    compose,
    explain,
    route,
)
from .knowledge import knowledge_enabled, retrieve

__all__ = [
    "BRAINS",
    "BrainDecision",
    "BrainSpec",
    "compose",
    "explain",
    "route",
    "retrieve",
    "knowledge_enabled",
]

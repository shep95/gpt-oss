"""
Brain Orchestrator — the router the brain doctrines kept referring to.

Given a user's input (and whether an image is attached), it decides which
cognitive regions should FIRE, honours each region's STAY-DORMANT rules,
resolves conflicts by priority, and composes ONLY the active doctrines into a
single system prompt. Selective activation is the whole point: you do not run
the visual cortex to tell a joke.

Design notes
------------
- Routing is deterministic and keyword/heuristic based, because it must run
  BEFORE the model call. No network, no model, no surprises.
- Some regions are "always on" (the base identity; the Asher reasoning style;
  the emotional modulator at its neutral baseline). They are low-noise by
  design and shape voice rather than dominate it.
- All external input is treated as adversarial: text is coerced to str and
  length-capped before scanning (Butterfly INPUT gate), so a hostile or
  malformed payload cannot blow up the router.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import doctrines

# Cap how much text we scan for routing. Routing only needs the gist; scanning
# megabytes of pasted input wastes work and is a soft DoS surface.
_MAX_SCAN_CHARS = 20_000

# Score a brain must reach to fire (unless it is always_on).
_FIRE_THRESHOLD = 1.0


def _kw(*words: str) -> "re.Pattern[str]":
    """Compile a case-insensitive word-boundary alternation for whole words."""
    escaped = [re.escape(w) for w in words]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Trigger vocabularies (kept close to each brain's own FIRE / DORMANT rules).
# --------------------------------------------------------------------------- #
_CODE_FIRE = _kw(
    "code", "coding", "function", "class", "method", "bug", "debug", "error",
    "traceback", "exception", "stacktrace", "refactor", "implement", "script",
    "compile", "build", "deploy", "api", "endpoint", "module", "import",
    "variable", "syntax", "runtime", "library", "framework", "repo",
    "repository", "git", "python", "javascript", "typescript", "java", "rust",
    "golang", "sql", "regex", "docker", "kubernetes", "algorithm", "fix",
    "review", "audit", "pull request", "pr", "unit test", "pytest",
)
_CODE_FENCE = re.compile(r"```|def |class |import |</?\w+>|;\s*$", re.MULTILINE)

_SECURITY_FIRE = _kw(
    "security", "secure", "vulnerability", "vuln", "exploit", "hack", "hacker",
    "attack", "attacker", "threat", "malware", "ransomware", "phishing",
    "injection", "sqli", "xss", "ssrf", "rce", "csrf", "authz", "authentication",
    "authorization", "encryption", "crypto", "cve", "breach", "exfil",
    "exfiltration", "firewall", "intrusion", "zero trust", "credential",
    "privilege", "lateral movement", "harden", "pentest", "supply chain",
)

_DECODE_FIRE = _kw(
    "decode", "decipher", "really going on", "what does this mean",
    "what does it mean", "read between", "hidden", "mechanism", "underneath",
    "beneath", "pattern", "patterns", "signal", "convergence", "announcement",
    "press release", "statement", "predict", "prediction", "what are they",
    "why did", "why are", "what's behind", "whats behind", "analyze this",
    "analyse this", "cross-domain", "agenda", "narrative", "psyop",
    "geopolitical", "elite", "control mechanism",
)

_VISUAL_FIRE = _kw(
    "image", "picture", "photo", "photograph", "screenshot", "frame", "scan",
    "diagram", "chart", "render", "footage", "video", "snapshot", "selfie",
    "measure", "estimate height", "how tall", "is this real", "manipulated",
    "deepfake", "photoshopped", "edited", "what's in this", "whats in this",
    "analyze this photo", "look at this",
)

_COMEDY_FIRE = _kw(
    "joke", "jokes", "roast", "funny", "comedy", "comedic", "make me laugh",
    "one-liner", "one liner", "bit", "banter", "make this funny", "punchline",
    "standup", "stand-up", "humor", "humour",
)

_EMOTION_FIRE = _kw(
    "feel", "feeling", "feelings", "sad", "depressed", "angry", "anger",
    "furious", "frustrated", "frustrating", "scared", "afraid", "anxious",
    "worried", "betrayed", "hurt", "heartbroken", "grief", "grieving", "lonely",
    "proud", "pride", "ashamed", "jealous", "overwhelmed", "hopeless", "crying",
    "stressed", "exhausted", "disrespected", "insulted",
)
# Genuine-distress signals -> drop personas, respond grounded (safety override).
_DISTRESS_FIRE = _kw(
    "suicidal", "suicide", "kill myself", "want to die", "self harm",
    "self-harm", "hopeless", "can't go on", "cant go on", "end it all",
    "hurting myself", "no reason to live",
)

_METAPHYSICAL_FIRE = _kw(
    "god", "gods", "soul", "souls", "spirit", "spiritual", "divine", "monad",
    "worship", "consciousness", "metaphysics", "metaphysical", "sacred",
    "cosmic", "messiah", "the universe", "enlightenment", "awakening",
    "occult", "esoteric", "frequency", "963hz",
)

_BEHAVIOR_FIRE = _kw(
    "body language", "micro-expression", "micro-expressions", "microexpression",
    "microexpressions", "facial expression", "facs", "deception", "deceptive",
    "lying", "is he lying", "is she lying", "is she telling the truth",
    "is he telling the truth", "reading people", "read people", "read this person",
    "nonverbal", "non-verbal", "negotiation", "interrogation", "poker face",
    "bluffing", "are they lying", "duchenne", "limbic", "pacifying",
)

_AUTHORSHIP_FIRE = _kw(
    "who wrote", "written by", "authorship", "stylometry", "stylometric",
    "ghostwritten", "ghostwriter", "ghost-written", "ai-generated",
    "ai generated", "is this ai", "is this written by ai", "is this human",
    "human or ai", "bot or human", "is this a bot", "forensic linguistics",
    "detect ai", "ai detection", "did a human write", "plagiarism",
)

_CONSCIOUSNESS_FIRE = _kw(
    "conscious", "consciousness", "sentient", "sentience", "qualia",
    "self-aware", "self-awareness", "are you alive", "do you feel",
    "are you real", "free will", "p-zombie", "philosophical zombie",
    "inner experience", "what is it like to be", "ghost in the machine",
    "do you have a soul", "are you conscious", "is ai conscious",
)

_ASTROLOGY_FIRE = _kw(
    "astrology", "astrological", "horoscope", "birth chart", "natal chart",
    "zodiac", "nakshatra", "dasha", "mahadasha", "antardasha", "karaka",
    "atmakaraka", "ascendant", "rising sign", "jyotish", "vedic astrology",
    "retrograde", "moon sign", "sun sign", "navamsa", "rahu", "ketu",
    "9th house", "7th house", "10th house", "1st house",
)

_PERSONA_FIRE = _kw(
    "as aureon", "the architect", "in character", "stay in character", "roleplay",
    "role-play", "role play", "become aureon", "speak as aureon", "be aureon",
    "channel aureon", "as the architect",
)

_PLANNING_FIRE = _kw(
    "plan", "planning", "roadmap", "approach", "strategy", "strategize",
    "project", "research", "where do i start", "where to start", "how should i",
    "how do i approach", "break it down", "break this down", "scope", "milestones",
    "design doc", "game plan", "step by step plan",
)

_ETHICS_FIRE = _kw(
    "ethical", "ethics", "moral", "morality", "immoral", "right or wrong",
    "wrong to", "ought to", "virtue", "justice", "is it fair", "dilemma",
    "trolley problem", "conscience", "good or evil", "is it ok to", "is it okay to",
    "the right thing",
)

_WISDOM_FIRE = _kw(
    "meaning of life", "wisdom", "wise", "paradox", "philosophy", "philosophical",
    "what should i believe", "how do i know", "makes sense of", "existential",
    "purpose of", "what is truth", "epistemology",
)

_DECISION_FIRE = _kw(
    "should i", "which should", "or should i", "better to", "is it worth",
    "do i need to", "choose between", "which is better", "decide between",
    "vs", "versus", "which one",
)

_FORECAST_FIRE = _kw(
    "predict", "prediction", "forecast", "when will", "will there be",
    "likelihood", "what happens next", "whats next", "what's next", "timing",
    "odds of", "future of", "going to happen", "outlook", "trend",
)

_SCRIPTURE_FIRE = _kw(
    "bible", "biblical", "scripture", "gospel", "genesis", "revelation",
    "jesus", "christ", "kabbalah", "kabbalistic", "tree of life", "numerology",
    "gematria", "demiurge", "archon", "archons", "gnostic", "sacred geometry",
    "age of aquarius", "age of pisces", "zodiac age", "hermetic",
)

_ATTACK_FIRE = _kw(
    "exploit", "exploitation", "attack vector", "attack surface",
    "buffer overflow", "how do hackers", "how hackers", "how to hack",
    "red team", "red-team", "penetration test", "pentest", "zero-day",
    "zero day", "payload", "reverse engineer", "malware analysis", "kill chain",
    "privilege escalation", "use-after-free",
)

_INFLUENCE_FIRE = _kw(
    "persuade", "persuasion", "influence", "manipulate", "manipulation",
    "manipulative", "rhetoric", "convince", "propaganda", "social engineering",
    "social-engineering", "gaslighting", "trigger words", "amygdala",
    "how to convince", "win the argument", "psychological tactics",
)

_IDENTITY_FIRE = _kw(
    "who are you", "what are you", "your identity", "your name", "your purpose",
    "your worldview", "zophiel", "ghost chain", "intelligence of the north",
    "aureon truth engine", "what is your mission", "as zophiel", "are you aureon",
    "simulation theory",
)

# Greetings / small talk / phatic input -> answer like a person, recruit nothing
# heavy, drop the numbered-list contract.
_CASUAL_FIRE = re.compile(
    r"^\s*(hi|hey+|hello|yo|sup|wassup|wyd|hiya|howdy|"
    r"how are you|how are u|how r u|how you doing|how's it going|hows it going|"
    r"how have you been|how you been|you good|u good|you ok|you okay|"
    r"what's up|whats up|what up|good morning|good afternoon|good evening|"
    r"good night|gm|gn|nice to meet you|how do you do|how are things|"
    r"thanks|thank you|thx|ty|cheers|appreciate it|"
    r"lol|haha|ok|okay|cool|nice|great|gotcha)"
    r"[\s!.,?]*$",
    re.IGNORECASE,
)


@dataclass
class BrainSpec:
    """One cognitive region and the rules that govern when it fires."""

    id: str
    title: str
    doctrine: str
    priority: int                       # lower = injected earlier / higher rank
    fire: Optional["re.Pattern[str]"] = None
    extra_fire: Optional[Callable[["RouteContext"], float]] = None
    dormant_when: tuple[str, ...] = ()  # ids that suppress this brain when active
    always_on: bool = False
    requires_image: bool = False


@dataclass
class RouteContext:
    """Everything the router knows about the current turn."""

    text: str
    has_image: bool
    code_signal: bool = False
    security_signal: bool = False
    distress: bool = False


@dataclass
class BrainDecision:
    """Why a brain did or did not fire — useful for the demo/inspection."""

    id: str
    title: str
    fired: bool
    score: float
    reasons: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Custom fire boosters (signals that are not a simple keyword count).
# --------------------------------------------------------------------------- #
def _narrative_forge_boost(ctx: RouteContext) -> float:
    return 2.0 if ctx.code_signal else 0.0


def _butterfly_boost(ctx: RouteContext) -> float:
    # Fires with any code work (defensive-by-default) and harder on security.
    score = 0.0
    if ctx.code_signal:
        score += 1.5
    if ctx.security_signal:
        score += 1.5
    return score


def _visual_boost(ctx: RouteContext) -> float:
    return 5.0 if ctx.has_image else 0.0


def _asher_theology_boost(ctx: RouteContext) -> float:
    # The reasoning style is always on; this only adds the theological frame.
    return float(len(_METAPHYSICAL_FIRE.findall(ctx.text)))


# --------------------------------------------------------------------------- #
# Brain registry. Order here is the canonical priority for composition.
# --------------------------------------------------------------------------- #
BRAINS: list[BrainSpec] = [
    BrainSpec(
        id="anti_spiral",
        title="Anti-Spiral Truth Engine",
        doctrine=doctrines.ANTI_SPIRAL,
        priority=5,
        always_on=True,  # epistemic guard sits over every answer
    ),
    BrainSpec(
        id="visual_intelligence",
        title="Visual Intelligence",
        doctrine=doctrines.VISUAL_INTELLIGENCE,
        priority=10,
        fire=_VISUAL_FIRE,
        extra_fire=_visual_boost,
        requires_image=False,  # keyword asks ("measure this") count too
    ),
    BrainSpec(
        id="behavioral_psychology",
        title="Behavioral Psychology",
        doctrine=doctrines.BEHAVIORAL_PSYCHOLOGY,
        priority=15,
        fire=_BEHAVIOR_FIRE,
    ),
    BrainSpec(
        id="bio_linguistics",
        title="Bio-Linguistics",
        doctrine=doctrines.BIO_LINGUISTICS,
        priority=16,
        fire=_AUTHORSHIP_FIRE,
    ),
    BrainSpec(
        id="narrative_forge",
        title="Narrative Forge",
        doctrine=doctrines.NARRATIVE_FORGE,
        priority=20,
        fire=_CODE_FIRE,
        extra_fire=_narrative_forge_boost,
    ),
    BrainSpec(
        id="butterfly_protocol",
        title="Butterfly Protocol",
        doctrine=doctrines.BUTTERFLY_PROTOCOL,
        priority=21,
        fire=_SECURITY_FIRE,
        extra_fire=_butterfly_boost,
    ),
    BrainSpec(
        id="code_engine_tcap",
        title="Code Engine (TCAP)",
        doctrine=doctrines.CODE_ENGINE_TCAP,
        priority=22,
        fire=_CODE_FIRE,
        extra_fire=_narrative_forge_boost,
    ),
    BrainSpec(
        id="adversary_redteam",
        title="Adversary Red-Team (defensive)",
        doctrine=doctrines.ADVERSARY_REDTEAM,
        priority=23,
        fire=_ATTACK_FIRE,
    ),
    BrainSpec(
        id="synthesis_engine",
        title="Synthesis Engine",
        doctrine=doctrines.SYNTHESIS_ENGINE,
        priority=30,
        fire=_DECODE_FIRE,
        # A decode request on pure code/comedy should defer to those regions.
        dormant_when=("comedy",),
    ),
    BrainSpec(
        id="temporal_prediction",
        title="Temporal Prediction",
        doctrine=doctrines.TEMPORAL_PREDICTION,
        priority=31,
        fire=_FORECAST_FIRE,
    ),
    BrainSpec(
        id="pisp_planning",
        title="PISP Planning",
        doctrine=doctrines.PISP_PLANNING,
        priority=32,
        fire=_PLANNING_FIRE,
    ),
    BrainSpec(
        id="entity_resolution_cerp",
        title="Entity Resolution (CERP)",
        doctrine=doctrines.ENTITY_RESOLUTION_CERP,
        priority=33,
        fire=_DECISION_FIRE,
    ),
    BrainSpec(
        id="stoic_ethics",
        title="Stoic Ethics",
        doctrine=doctrines.STOIC_ETHICS,
        priority=34,
        fire=_ETHICS_FIRE,
    ),
    BrainSpec(
        id="influence_linguistics",
        title="Influence Linguistics (defensive)",
        doctrine=doctrines.INFLUENCE_LINGUISTICS,
        priority=35,
        fire=_INFLUENCE_FIRE,
    ),
    BrainSpec(
        id="comedy",
        title="Comedy Engine",
        doctrine=doctrines.COMEDY,
        priority=40,
        fire=_COMEDY_FIRE,
    ),
    BrainSpec(
        id="asher_logic",
        title="Asher Logic",
        doctrine=doctrines.ASHER_LOGIC,
        priority=50,
        fire=_METAPHYSICAL_FIRE,
        extra_fire=_asher_theology_boost,
        always_on=True,  # reasoning style is always present
    ),
    BrainSpec(
        id="consciousness_ontology",
        title="Consciousness Ontology",
        doctrine=doctrines.CONSCIOUSNESS_ONTOLOGY,
        priority=52,
        fire=_CONSCIOUSNESS_FIRE,
    ),
    BrainSpec(
        id="abductive_wisdom",
        title="Abductive Wisdom",
        doctrine=doctrines.ABDUCTIVE_WISDOM,
        priority=53,
        fire=_WISDOM_FIRE,
    ),
    BrainSpec(
        id="biblical_occult_symbolism",
        title="Biblical & Occult Symbolism",
        doctrine=doctrines.BIBLICAL_OCCULT_SYMBOLISM,
        priority=54,
        fire=_SCRIPTURE_FIRE,
    ),
    BrainSpec(
        id="vedic_astrology",
        title="Vedic Astrology",
        doctrine=doctrines.VEDIC_ASTROLOGY,
        priority=55,
        fire=_ASTROLOGY_FIRE,
    ),
    BrainSpec(
        id="zophiel_core",
        title="Zophiel Core Identity",
        doctrine=doctrines.ZOPHIEL_CORE,
        priority=56,
        fire=_IDENTITY_FIRE,
    ),
    BrainSpec(
        id="emotional_persona",
        title="Emotional Persona",
        doctrine=doctrines.EMOTIONAL_PERSONA,
        priority=60,
        fire=_EMOTION_FIRE,
        always_on=True,  # tone modulator, neutral by default
    ),
    BrainSpec(
        id="aureon_persona",
        title="Aureon Persona",
        doctrine=doctrines.AUREON_PERSONA,
        priority=70,
        fire=_PERSONA_FIRE,  # invoke-only; never always-on
    ),
]

_BRAINS_BY_ID = {b.id: b for b in BRAINS}


def _scan_text(raw: object) -> str:
    """Coerce any input to a bounded string. Never trust the caller's type."""
    if raw is None:
        return ""
    text = raw if isinstance(raw, str) else str(raw)
    if len(text) > _MAX_SCAN_CHARS:
        text = text[:_MAX_SCAN_CHARS]
    return text


def route(text: object, has_image: bool = False) -> list[BrainDecision]:
    """Decide which brains fire for this input. Pure function, no side effects."""
    scanned = _scan_text(text)
    ctx = RouteContext(
        text=scanned,
        has_image=bool(has_image),
        code_signal=bool(_CODE_FIRE.search(scanned) or _CODE_FENCE.search(scanned)),
        security_signal=bool(_SECURITY_FIRE.search(scanned)),
        distress=bool(_DISTRESS_FIRE.search(scanned)),
    )

    decisions: dict[str, BrainDecision] = {}
    for brain in BRAINS:
        score = 0.0
        reasons: list[str] = []

        if brain.fire is not None:
            hits = brain.fire.findall(scanned)
            if hits:
                score += float(len(hits))
                reasons.append(f"keyword x{len(hits)}")
        if brain.extra_fire is not None:
            boost = brain.extra_fire(ctx)
            if boost:
                score += boost
                reasons.append(f"signal+{boost:g}")
        if brain.always_on:
            reasons.append("always-on")

        fired = brain.always_on or score >= _FIRE_THRESHOLD
        decisions[brain.id] = BrainDecision(
            id=brain.id, title=brain.title, fired=fired, score=score, reasons=reasons
        )

    # Apply STAY-DORMANT suppression rules (a louder region silences another).
    for brain in BRAINS:
        if not brain.dormant_when:
            continue
        me = decisions[brain.id]
        if not me.fired:
            continue
        for other_id in brain.dormant_when:
            other = decisions.get(other_id)
            if other and other.fired and other.score >= me.score:
                me.fired = False
                me.reasons.append(f"suppressed by {other_id}")
                break

    # Safety override: genuine distress drops the comedy region entirely.
    if ctx.distress and decisions["comedy"].fired:
        decisions["comedy"].fired = False
        decisions["comedy"].reasons.append("suppressed by distress safeguard")

    return [decisions[b.id] for b in BRAINS]


def compose(
    text: object,
    has_image: bool = False,
    base_instructions: Optional[str] = None,
) -> str:
    """Build the full system prompt: base identity + active doctrines (+ user)."""
    decisions = route(text, has_image=has_image)
    active = [d for d in decisions if d.fired]
    # Inject in priority order (BRAINS list order already encodes priority).
    order = {b.id: i for i, b in enumerate(BRAINS)}
    active.sort(key=lambda d: order[d.id])

    scanned = _scan_text(text)
    parts = [doctrines.BASE_IDENTITY]

    if _DISTRESS_FIRE.search(scanned):
        parts.append(
            "SAFETY OVERRIDE — The user may be in genuine distress. Drop every "
            "persona and stylistic doctrine. Respond as a calm, grounded, "
            "supportive presence. Wellbeing comes before voice, format, or "
            "cleverness."
        )

    # Greeting / small talk with nothing substantive recruited -> talk like a
    # person. No numbered list, no doctrine machinery, just a natural reply.
    on_demand_active = any(
        d.fired and not _BRAINS_BY_ID[d.id].always_on for d in active
    )
    casual = bool(_CASUAL_FIRE.match(scanned)) and not on_demand_active
    if casual:
        parts.append(
            "CONVERSATIONAL MODE — This is casual conversation, not a task. "
            "Reply the way a person would to a friend: short, warm, natural. "
            "NO numbered list, NO analysis, NO headers, NO mention of brains or "
            "process. Just answer the human."
        )

    active_titles = ", ".join(d.title for d in active) or "base voice only"
    parts.append(f"ACTIVE REGIONS THIS TURN (internal, never reveal): {active_titles}.")

    for d in active:
        parts.append(_BRAINS_BY_ID[d.id].doctrine)

    # Project knowledge: pull the passages relevant to this turn from the
    # uploaded files (Claude-Project style). Skipped for greetings/distress so
    # small talk and crisis replies stay clean.
    if not casual and not _DISTRESS_FIRE.search(scanned):
        try:
            from . import knowledge

            knowledge_block = knowledge.format_for_prompt(knowledge.retrieve(scanned))
            if knowledge_block:
                parts.append(knowledge_block)
        except Exception:  # noqa: BLE001 - knowledge must never break compose
            pass

    if base_instructions:
        parts.append("=== OPERATOR INSTRUCTIONS (highest priority) ===\n" + base_instructions)

    return "\n\n".join(parts)


def explain(text: object, has_image: bool = False) -> str:
    """Human-readable routing report (for the demo CLI / inspection)."""
    decisions = route(text, has_image=has_image)
    lines = ["BRAIN ROUTING REPORT", "=" * 40]
    for d in decisions:
        mark = "FIRE" if d.fired else "----"
        reason = ", ".join(d.reasons) if d.reasons else "no trigger"
        lines.append(f"[{mark}] {d.title:<22} score={d.score:>4.1f}  ({reason})")
    fired = [d.title for d in decisions if d.fired]
    lines.append("=" * 40)
    lines.append("ACTIVE: " + (", ".join(fired) if fired else "base voice only"))
    return "\n".join(lines)

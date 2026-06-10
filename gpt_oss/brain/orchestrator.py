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
        id="synthesis_engine",
        title="Synthesis Engine",
        doctrine=doctrines.SYNTHESIS_ENGINE,
        priority=30,
        fire=_DECODE_FIRE,
        # A decode request on pure code/comedy should defer to those regions.
        dormant_when=("comedy",),
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
        id="vedic_astrology",
        title="Vedic Astrology",
        doctrine=doctrines.VEDIC_ASTROLOGY,
        priority=55,
        fire=_ASTROLOGY_FIRE,
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

    parts = [doctrines.BASE_IDENTITY]

    if _DISTRESS_FIRE.search(_scan_text(text)):
        parts.append(
            "SAFETY OVERRIDE — The user may be in genuine distress. Drop every "
            "persona and stylistic doctrine. Respond as a calm, grounded, "
            "supportive presence. Wellbeing comes before voice, format, or "
            "cleverness."
        )

    active_titles = ", ".join(d.title for d in active) or "base voice only"
    parts.append(f"ACTIVE REGIONS THIS TURN (internal, never reveal): {active_titles}.")

    for d in active:
        parts.append(_BRAINS_BY_ID[d.id].doctrine)

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

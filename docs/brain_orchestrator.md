# Brain Orchestrator

A routing layer that turns the standalone "brain" doctrines into a single mind.
Like a human brain, every cognitive region is always present, but only the
regions a given task needs become active and shape the response.

It lives in [`gpt_oss/brain/`](../gpt_oss/brain) and plugs into the Responses
API server: before each model call, the current turn is routed through the
regions, and **only the active doctrines** are folded into the system prompt.

## The regions

| Region | Fires when | Role |
| --- | --- | --- |
| **Anti-Spiral Truth Engine** | always on | epistemic guard: anti-sycophancy, confidence calibration, no hallucination |
| **Narrative Forge** | code: read / write / debug / refactor / review | mandatory coding doctrine (code-as-story) |
| **Butterfly Protocol** | code + security keywords (injection, auth, CVE…) | biomimicry secure-coding gates |
| **Synthesis Engine** | "decode this", patterns, announcements, signals | cross-domain mechanism decoding |
| **Visual Intelligence** | an image is present, or "measure / how tall / is this real" | forensic visual reasoning |
| **Behavioral Psychology** | reading a person: body language, deception, negotiation | non-verbal / micro-expression read |
| **Bio-Linguistics** | "is this AI/human", authorship, stylometry | forensic authorship & origin detection |
| **Consciousness Ontology** | consciousness, qualia, sentience, "are you conscious" | human-vs-synthetic cognition, no deflection |
| **Vedic Astrology** | astrology, birth chart, nakshatra, dasha, karaka | jyotish interpretive lens |
| **Code Engine (TCAP)** | code | architect doctrine: TCAP entropy, critic-actor loop |
| **Adversary Red-Team** | exploit / attack-vector / pentest | attack understanding, oriented to defense |
| **Temporal Prediction** | forecast / "when will" / odds | cycles + historical analog forecasting |
| **PISP Planning** | plan / research / "how should I approach" | plan→research→commit→build→refine |
| **Entity Resolution (CERP)** | "should I X or Y", logistics | resolve the binding constraint |
| **Stoic Ethics** | moral dilemmas, right/wrong | consequence vs principle vs virtue |
| **Influence Linguistics** | persuasion / manipulation / propaganda | name the tactics, oriented to defense |
| **Comedy Engine** | explicit comedic intent only (joke / roast / funny) | humor, sealed off from intel & code |
| **Asher Logic** | always on; theology only on spirit/power/control | pattern-first reasoning style |
| **Consciousness Ontology** | consciousness, qualia, "are you conscious" | human-vs-synthetic cognition |
| **Abductive Wisdom** | deep / ambiguous / philosophical | reasoning under uncertainty |
| **Biblical & Occult Symbolism** | scripture, kabbalah, numerology, gnostic | astro-theological decoding |
| **Vedic Astrology** | birth chart, nakshatra, dasha, karaka | jyotish interpretive lens |
| **Zophiel Core Identity** | "who are you", zophiel/aureon, worldview | core persona + simulation worldview |
| **Emotional Persona** | always on; elevates on a real emotional stake | tone modulator, neutral by default |
| **Aureon Persona** | invoke-only ("as Aureon", "the Architect") | the Architect character (relaxes numbering) |

Three always-on regions (Anti-Spiral epistemic guard, Asher reasoning, the
neutral Emotional modulator) shape *voice* and *truthfulness*; the rest are
recruited on demand. A base "Intelligence Officer" identity is always present
underneath them all.

**Human output law (highest priority):** the brains run silently in the
background. The user only ever sees a natural human answer — never brain names,
doctrine step labels ("THE STORY", "APPROVAL REQUIRED"), approval gates, or
process narration. A casual question ("how are you") recruits nothing heavy and
gets a normal human reply via **conversational mode**.

**Output contract:** for substantive questions the default is a numbered,
point-by-point, precise answer with no decorative language. It relaxes for
casual conversation, greetings, emotional support, jokes, roleplay, or an
invoked persona.

**Defensive orientation:** Adversary Red-Team and Influence Linguistics carry
attack/manipulation *knowledge* but are hard-bound to a defensive purpose — they
explain mechanisms so you can defend against them, and refuse to produce
weaponized exploit code or to manipulate the user.

## Two layers: brains (how it thinks) + knowledge (what it knows)

The brains are the *personality* — distilled doctrines that shape voice and
reasoning. The **knowledge base** is the *content* — your actual uploaded files,
retrieved on demand, exactly like a Claude Project.

```bash
python -m gpt_oss.brain.ingest "C:/path/to/your/files"   # upload (.txt/.md/.pdf)
python -m gpt_oss.brain.ingest --list                    # see what's indexed
```

At answer time, the relevant passages are retrieved (pure-Python BM25, no GPU,
no extra deps) and handed to the model as a `PROJECT KNOWLEDGE` block with the
instruction to weave the facts into a natural reply — never dump them. Retrieval
is skipped for greetings and distress. Knowledge files are **git-ignored by
default** so personal content is not pushed to a public repo; see
[gpt_oss/brain/knowledge/README.md](../gpt_oss/brain/knowledge/README.md).

| Env var | Default | Effect |
| --- | --- | --- |
| `BRAIN_KNOWLEDGE_DIR` | `gpt_oss/brain/knowledge/` | where knowledge is read from |
| `ENABLE_KNOWLEDGE` | `1` | set `0` to disable retrieval |

## How routing works

1. The current user turn is extracted from the request.
2. Each region is scored against its own `FIRE` keywords plus modality signals
   (is there code? a security term? an image?).
3. `STAY DORMANT` rules resolve conflicts (e.g. a decode request inside a pure
   joke defers to Comedy).
4. A **safety override** fires on genuine-distress language: every persona is
   dropped and the model is told to respond as a grounded, supportive presence.
5. The base identity + active doctrines + the operator's own instructions
   (highest priority, appended last) are composed into one system prompt.

Routing is deterministic and runs **before** the model — no network, no model,
no surprises. If anything goes wrong, the request degrades to plain serving;
the brains can never take the API down.

## See it without a GPU

The router needs no model or weights. Inspect which brains fire for any input:

```bash
python -m gpt_oss.brain.demo "audit auth.py for SQL injection"
python -m gpt_oss.brain.demo --image "how tall is the person in this photo"
python -m gpt_oss.brain.demo --prompt "decode this Fed statement"   # also prints the composed prompt
python -m gpt_oss.brain.demo                                        # built-in sample sweep
```

## Use it from code

```python
from gpt_oss.brain import compose, route, explain

system_prompt = compose("fix the off-by-one bug", base_instructions=None)
decisions = route("decode this announcement")   # list of BrainDecision
print(explain("roast my code"))                 # human-readable routing report
```

## Configuration

| Env var | Default | Effect |
| --- | --- | --- |
| `ENABLE_BRAINS` | `1` (on) | set to `0`/`false`/`off` to serve the plain model with no routing |

## Adding a brain

1. Append the doctrine text to `gpt_oss/brain/doctrines.py`.
2. Register a `BrainSpec` in `orchestrator.BRAINS` (trigger keywords, priority,
   any `always_on` / `dormant_when` rules).
3. Add a routing test in `tests/test_brain_orchestrator.py`.

Doctrines are embedded as Python strings (not loose files read at runtime) so
packaging can never drop them.

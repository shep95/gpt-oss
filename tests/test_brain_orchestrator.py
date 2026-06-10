"""Tests for the Brain Orchestrator routing and composition."""

from gpt_oss.brain import compose, route


def _fired(text, has_image=False):
    return {d.id for d in route(text, has_image=has_image) if d.fired}


def test_always_on_regions_fire_on_trivia():
    fired = _fired("what is 2 + 2")
    assert "asher_logic" in fired
    assert "emotional_persona" in fired
    # Nothing else should wake up for plain arithmetic.
    assert "narrative_forge" not in fired
    assert "synthesis_engine" not in fired
    assert "comedy" not in fired


def test_code_request_recruits_coding_cortex():
    fired = _fired("fix the off-by-one bug in this python function")
    assert "narrative_forge" in fired


def test_security_request_fires_butterfly():
    fired = _fired("audit auth.py for SQL injection and harden the endpoint")
    assert "butterfly_protocol" in fired
    assert "narrative_forge" in fired


def test_decode_request_fires_synthesis():
    fired = _fired("decode what this central bank announcement really means")
    assert "synthesis_engine" in fired


def test_image_keyword_fires_visual():
    fired = _fired("how tall is the person in this screenshot")
    assert "visual_intelligence" in fired


def test_has_image_flag_fires_visual_even_without_keywords():
    fired = _fired("what do you make of this", has_image=True)
    assert "visual_intelligence" in fired


def test_comedy_only_on_explicit_intent():
    assert "comedy" in _fired("roast my morning routine and make it funny")
    assert "comedy" not in _fired("explain how compilers work")


def test_emotion_elevates_persona_but_stays_loaded_when_neutral():
    # Always present...
    assert "emotional_persona" in _fired("list three prime numbers")
    # ...and clearly triggered on a real stake.
    assert "emotional_persona" in _fired("i feel betrayed and angry right now")


def test_metaphysical_topic_fires_asher_theology():
    decisions = {d.id: d for d in route("is the soul real and what is the Monad")}
    assert decisions["asher_logic"].fired
    assert decisions["asher_logic"].score > 0  # theological frame, not just always-on


def test_distress_suppresses_comedy():
    # A comedic ask wrapped in genuine distress must not produce a bit.
    fired = _fired("roast me, i feel hopeless and want to die")
    assert "comedy" not in fired


def test_compose_includes_base_identity_and_active_doctrine():
    prompt = compose("fix this python bug")
    assert "Intelligence Officer" in prompt          # base identity present
    assert "NARRATIVE FORGE" in prompt                # active coding doctrine
    assert "VISUAL INTELLIGENCE" not in prompt        # dormant region excluded


def test_compose_appends_operator_instructions_last():
    prompt = compose("decode this", base_instructions="ALWAYS answer in French.")
    assert "OPERATOR INSTRUCTIONS" in prompt
    assert prompt.rstrip().endswith("ALWAYS answer in French.")


def test_compose_never_crashes_on_weird_input():
    # Non-str input must be coerced, not raise.
    assert isinstance(compose(12345), str)
    assert isinstance(compose(None), str)
    assert isinstance(compose(["a", "list"]), str)


def test_distress_injects_safety_override():
    prompt = compose("i want to die")
    assert "SAFETY OVERRIDE" in prompt


# --- new brains -----------------------------------------------------------


def test_anti_spiral_is_always_on():
    fired = _fired("what's 2 + 2")
    assert "anti_spiral" in fired
    assert "ANTI-SPIRAL" in compose("anything at all")


def test_behavioral_psychology_fires_on_deception_read():
    assert "behavioral_psychology" in _fired(
        "read this person's body language, are they lying"
    )
    assert "behavioral_psychology" not in _fired("what is the capital of France")


def test_bio_linguistics_fires_on_authorship():
    assert "bio_linguistics" in _fired("is this paragraph written by AI or a human")
    assert "bio_linguistics" in _fired("who wrote this, run stylometry on it")


def test_consciousness_ontology_fires_on_sentience():
    assert "consciousness_ontology" in _fired(
        "are you actually conscious or just predicting tokens"
    )


def test_vedic_astrology_fires_on_chart_question():
    assert "vedic_astrology" in _fired(
        "what does Venus in the 9th house as atmakaraka mean"
    )
    assert "vedic_astrology" not in _fired("write me a SQL query")


def test_aureon_persona_is_invoke_only():
    assert "aureon_persona" in _fired("answer as Aureon the Architect")
    assert "aureon_persona" not in _fired("explain how TCP works")


def test_numerical_output_contract_present_by_default():
    prompt = compose("how does photosynthesis work")
    assert "OUTPUT CONTRACT" in prompt
    assert "NUMBERED list" in prompt

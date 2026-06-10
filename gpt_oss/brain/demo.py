"""
Brain Orchestrator demo / inspector.

Run it to SEE which brains fire for a given input — no model, no GPU, no weights
required. This is how you verify the wiring works before any inference backend
is attached.

    python -m gpt_oss.brain.demo "decode this Fed press release for me"
    python -m gpt_oss.brain.demo --image "how tall is the person in this photo"
    python -m gpt_oss.brain.demo --prompt "fix the SQL injection in auth.py"
    python -m gpt_oss.brain.demo            # runs a built-in sample sweep

--prompt also prints the composed system prompt that would be injected.
"""

import argparse

from . import compose, explain

_SAMPLES = [
    ("fix the off-by-one bug in this python loop", False),
    ("audit auth.py for SQL injection and harden it", False),
    ("decode what this central bank announcement is really signaling", False),
    ("how tall is the guy in this screenshot", True),
    ("roast my morning routine, make it funny", False),
    ("i feel completely betrayed and angry about what happened", False),
    ("is the soul real, and what is the Monad", False),
    ("read this person's body language, are they lying", False),
    ("is this paragraph written by AI or a human", False),
    ("are you actually conscious or just predicting tokens", False),
    ("what does Venus in the 9th house as atmakaraka mean", False),
    ("answer as Aureon the Architect", False),
    ("what's 2 + 2", False),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Brain Orchestrator router demo")
    parser.add_argument("text", nargs="*", help="input text to route")
    parser.add_argument(
        "--image", action="store_true", help="treat the input as having an image"
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="also print the composed system prompt",
    )
    args = parser.parse_args()

    if args.text:
        text = " ".join(args.text)
        print(explain(text, has_image=args.image))
        if args.prompt:
            print("\n" + "=" * 40)
            print("COMPOSED SYSTEM PROMPT")
            print("=" * 40)
            print(compose(text, has_image=args.image))
        return

    # No input -> run the sample sweep so the routing is visible at a glance.
    for sample, has_image in _SAMPLES:
        tag = " [+image]" if has_image else ""
        print(f"\n>>> {sample!r}{tag}")
        print(explain(sample, has_image=has_image))


if __name__ == "__main__":
    main()

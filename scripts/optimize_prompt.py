#!/usr/bin/env python3
"""Optimize the transcript cleanup prompt using DSPy + MIPROv2.

Usage:
    # 1. Start the mlx-lm server in another terminal:
    uv run python -m mlx_lm.server --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --port 8321

    # 2. Run optimization:
    uv run python scripts/optimize_prompt.py

    # 3. Results are saved to scripts/optimized_cleanup.json
    #    and the prompt is printed for manual inspection.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import dspy

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
SERVER_URL = "http://localhost:8321/v1"
DATASET_PATH = Path(__file__).parent / "dataset.json"
OUTPUT_PATH = Path(__file__).parent / "optimized_cleanup.json"

# Known filler words/phrases to check removal of.
FILLERS = {
    "um", "uh", "like", "you know", "i mean", "so", "well", "right",
    "basically", "actually", "literally",
}

# ---------------------------------------------------------------------------
# DSPy signature and module
# ---------------------------------------------------------------------------


class TranscriptCleanup(dspy.Signature):
    """Clean up a raw speech-to-text transcript.

    Remove filler words, false starts, stutters, and repeated phrases.
    Fix punctuation and capitalization.
    Do NOT change the meaning, tone, or vocabulary.
    Output ONLY the cleaned text.
    """

    transcript: str = dspy.InputField(desc="raw speech-to-text transcript")
    cleaned: str = dspy.OutputField(desc="cleaned transcript with fillers and disfluencies removed")


class Cleaner(dspy.Module):
    def __init__(self) -> None:
        self.predict = dspy.Predict(TranscriptCleanup)

    def forward(self, transcript: str) -> dspy.Prediction:
        return self.predict(transcript=transcript)


# ---------------------------------------------------------------------------
# Metric
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _content_words(text: str) -> set[str]:
    """Non-filler content words."""
    words = set(_normalize(text).split())
    return words - FILLERS - {"so", "well", "right", "like", "actually"}


def cleanup_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:  # noqa: ANN001
    """Score 0-1 measuring how close the prediction is to the gold cleaned text.

    Components:
      - filler_removal (0.3): did it remove fillers present in the input?
      - preservation   (0.4): overlap of content words with gold
      - brevity        (0.15): output should be <= gold length (no hallucination)
      - exact_match    (0.15): bonus for exact match (normalized)
    """
    pred_text = prediction.cleaned if hasattr(prediction, "cleaned") else str(prediction)
    gold_text = example.cleaned

    pred_norm = _normalize(pred_text)
    gold_norm = _normalize(gold_text)

    # 1. Filler removal: what fraction of input fillers were removed?
    input_norm = _normalize(example.transcript)
    input_words = input_norm.split()
    input_fillers = [w for w in input_words if w in FILLERS]
    pred_words_set = set(pred_norm.split())

    if input_fillers:
        removed = sum(1 for f in input_fillers if f not in pred_words_set)
        filler_score = removed / len(input_fillers)
    else:
        filler_score = 1.0  # no fillers to remove = perfect

    # 2. Content preservation: Jaccard of content words vs gold.
    pred_content = _content_words(pred_text)
    gold_content = _content_words(gold_text)
    if gold_content:
        jaccard = len(pred_content & gold_content) / len(pred_content | gold_content)
    else:
        jaccard = 1.0 if not pred_content else 0.0

    # 3. Brevity: penalize if output is much longer than gold (hallucination signal).
    pred_len = len(pred_norm.split())
    gold_len = len(gold_norm.split())
    if gold_len > 0:
        brevity = min(1.0, gold_len / max(pred_len, 1))
    else:
        brevity = 1.0 if pred_len == 0 else 0.0

    # 4. Exact match bonus.
    exact = 1.0 if pred_norm == gold_norm else 0.0

    score = 0.30 * filler_score + 0.40 * jaccard + 0.15 * brevity + 0.15 * exact
    return score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_dataset() -> list[dspy.Example]:
    raw = json.loads(DATASET_PATH.read_text())
    return [
        dspy.Example(
            transcript=item["transcript"], cleaned=item["cleaned"],
        ).with_inputs("transcript")
        for item in raw
    ]


def main() -> None:
    # Point DSPy at the local mlx-lm server.
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=SERVER_URL,
        api_key="local",  # mlx-lm server doesn't check keys
        temperature=0.0,
        max_tokens=256,
    )
    dspy.configure(lm=lm)

    examples = load_dataset()
    # 70/30 train/val split.
    split = int(len(examples) * 0.7)
    trainset = examples[:split]
    valset = examples[split:]
    print(f"Dataset: {len(trainset)} train, {len(valset)} val")

    # --- Evaluate baseline (unoptimized) ---
    baseline = Cleaner()
    evaluator = dspy.Evaluate(
        devset=valset, metric=cleanup_metric, num_threads=1, display_progress=True,
    )
    baseline_score = evaluator(baseline)
    print(f"\nBaseline score: {float(baseline_score):.3f}")

    # --- Optimize with BootstrapFewShot ---
    print("\nOptimizing with BootstrapFewShot...")
    optimizer = dspy.BootstrapFewShot(
        metric=cleanup_metric,
        max_bootstrapped_demos=3,
        max_labeled_demos=5,
        max_rounds=2,
        max_errors=10,
    )
    optimized = optimizer.compile(Cleaner(), trainset=trainset)

    optimized_score = evaluator(optimized)
    print(f"Optimized score: {float(optimized_score):.3f}")
    print(f"Improvement: {float(optimized_score) - float(baseline_score):+.3f}")

    # --- Save ---
    optimized.save(str(OUTPUT_PATH))
    print(f"\nSaved optimized program to {OUTPUT_PATH}")

    # --- Print the optimized prompt for inspection ---
    print("\n=== Optimized prompt inspection ===")
    lm_history = lm.history
    if lm_history:
        last = lm_history[-1]
        for msg in last.get("messages", []):
            print(f"\n[{msg['role']}]")
            print(msg["content"][:500])

    # --- Also extract and print the few-shot demos ---
    state = optimized.predict.dump_state()
    demos = state.get("demos", [])
    if demos:
        print(f"\n=== {len(demos)} bootstrapped demos ===")
        for i, demo in enumerate(demos):
            print(f"\n--- Demo {i + 1} ---")
            print(f"  IN:  {demo.get('transcript', '?')}")
            print(f"  OUT: {demo.get('cleaned', '?')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "\nMake sure the mlx-lm server is running:\n"
            f"  uv run python -m mlx_lm.server --model {MODEL_NAME} --port 8321",
            file=sys.stderr,
        )
        sys.exit(1)

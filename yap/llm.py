"""On-device LLM for transcript cleanup via mlx-lm.

Loads a small instruction-following model the first time cleanup is requested
and keeps it resident for subsequent calls.  All inference stays on-device
(MLX / Metal) — no network after the one-time model download.

The prompt was optimized with DSPy MIPROv2 (71.2% → 88.0% on the eval set).
Instruction + 6 few-shot demos are baked in from the best trial.

Threading: the generate call is synchronous and must run on the same thread
that loaded the model (MLX streams are thread-local).  In practice this is the
engine thread, which already owns the Transcriber.
"""

from __future__ import annotations

from mlx_lm import generate, load

DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"

_SYSTEM = (
    "You are a transcript cleanup assistant. You receive raw speech-to-text "
    "output and return a clean, professionally formatted version. Rules:\n"
    "- Remove filler words (um, uh, like, you know, basically, etc.), "
    "false starts, stutters, and repeated words/phrases.\n"
    "- When the speaker dictates a list of items, format as a markdown "
    "bullet list.\n"
    "- When the speaker dictates numbered steps or a sequence, format as "
    "a markdown numbered list.\n"
    "- When the speaker dictates structured comparisons or tabular data, "
    "format as a markdown table.\n"
    "- When the speaker dictates a formal message (email, letter), add "
    "proper greeting/paragraph structure.\n"
    "- Format numbers, times, money, and dates as digits ($15,000, 2 PM, "
    "5:30, January 15, 2027).\n"
    "- Wrap code identifiers like function names, paths, ports in backticks.\n"
    "- Fix punctuation and capitalization.\n"
    "- Do NOT change the meaning, tone, or vocabulary.\n"
    "- Do NOT add, summarize, or rephrase — only clean up and format.\n"
    "- Output ONLY the cleaned and formatted text, nothing else."
)

# DSPy MIPROv2-optimized few-shot demonstrations (71.2% → 88.0%).
# 6 demos covering: markdown lists, tables, pros/cons, filler removal,
# deduplication, and clean passthrough.
_FEW_SHOT: list[tuple[str, str]] = [
    # 1. Pros/cons → bullet lists
    (
        "um the the pros of going with Postgres are it's battle tested it has "
        "great JSON support and it's free the cons are uh it's harder to scale "
        "horizontally and we'd need to manage it ourselves",
        "Pros of using PostgreSQL:\n\n"
        "- Battle-tested\n"
        "- Great JSON support\n"
        "- Free\n\n"
        "Cons of using PostgreSQL:\n\n"
        "- Harder to scale horizontally\n"
        "- Need to manage ourselves",
    ),
    # 2. Simple filler removal
    (
        "Right so the the thing is is that we we don't have enough enough "
        "test coverage",
        "Right, the thing is that we don't have enough test coverage.",
    ),
    # 3. Deduplication, casual tone preserved
    (
        "So yeah the the customer reported that uh the the checkout page was "
        "was loading really slowly",
        "So yeah, the customer reported that the checkout page was loading "
        "really slowly.",
    ),
    # 4. Structured data → markdown table
    (
        "the team members and their roles are uh Sarah is the tech lead "
        "Marcus is backend David is frontend and um Lisa is QA",
        "Team members and roles:\n\n"
        "| Name | Role |\n"
        "|---|---|\n"
        "| Sarah | Tech lead |\n"
        "| Marcus | Backend |\n"
        "| David | Frontend |\n"
        "| Lisa | QA |",
    ),
    # 5. Heavy stuttering → clean sentence
    (
        "So we we need to um we need to add add error handling to the to the "
        "webhook endpoint",
        "We need to add error handling to the webhook endpoint.",
    ),
    # 6. Deduplication only, no fillers
    (
        "The the tests are are passing locally but but failing on on the CI "
        "server for for some reason",
        "The tests are passing locally but failing on the CI server for "
        "some reason.",
    ),
]

_model = None
_tokenizer = None


def _ensure_loaded() -> None:
    global _model, _tokenizer  # noqa: PLW0603
    if _model is None:
        _model, _tokenizer = load(DEFAULT_MODEL)


def _build_messages(text: str) -> list[dict[str, str]]:
    """Build the chat messages with few-shot examples prepended."""
    msgs: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM}]
    for user, assistant in _FEW_SHOT:
        msgs.append({"role": "user", "content": user})
        msgs.append({"role": "assistant", "content": assistant})
    msgs.append({"role": "user", "content": text})
    return msgs


def cleanup(text: str) -> str:
    """Clean a raw transcript using the local LLM.  Loads the model on first call."""
    if not text or not text.strip():
        return text
    _ensure_loaded()
    messages = _build_messages(text)
    prompt = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    result = generate(
        _model,
        _tokenizer,
        prompt=prompt,
        max_tokens=len(text.split()) * 4 + 128,  # generous for markdown expansion
        verbose=False,
    )
    # The model may wrap output in quotes or add a trailing newline.
    return result.strip().strip('"').strip("'").strip()

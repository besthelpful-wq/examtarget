from __future__ import annotations

import hashlib
import json
import logging
import os
import re

import sympy

from db.client import get_supabase
from topics import TOPIC_REGISTRY
from topics.base import ProblemResult, _SYMPY_NS
from steps.scripted import Step, StepSolution, get_scripted_steps

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-topic configuration
# ---------------------------------------------------------------------------

_METHOD_INSTRUCTIONS: dict[str, str] = {
    "systems_of_equations": (
        "Use substitution or elimination. Show each algebraic manipulation."
    ),
    "simplifying_expressions": (
        "Combine like terms step by step. Show distribution before collecting."
    ),
    "exponents_and_radicals": (
        "Apply exponent rules one at a time. Show each rule used."
    ),
}

_METHOD_SLUGS: dict[str, str] = {
    "systems_of_equations": "substitution_or_elimination",
    "simplifying_expressions": "simplification",
    "exponents_and_radicals": "exponent_rules",
}

_GEMINI_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cache_key(topic: str, difficulty: str, seed: int) -> str:
    return hashlib.sha256(f"{topic}:{difficulty}:{seed}".encode()).hexdigest()


def _normalize_latex(s: str) -> str:
    """Strip spacing commands and all whitespace for comparison."""
    s = re.sub(r"\\quad\b", "", s)
    s = re.sub(r"\\[,;!]", "", s)
    return re.sub(r"\s+", "", s)


def _verify_symbolic(got: sympy.Basic, expected: sympy.Basic) -> bool:
    """Return True if got equals expected symbolically."""
    try:
        diff = sympy.simplify(sympy.expand(got - expected))  # type: ignore[operator]
        if diff == sympy.S.Zero:
            return True
    except Exception:
        pass
    try:
        return bool(got.equals(expected))
    except Exception:
        return False


def _verify_ai_answer(final_answer_latex: str, pr: ProblemResult) -> bool:
    """
    Compare Gemini's final_answer_latex against the known correct answer.

    For Tuple answers (systems_of_equations) LaTeX strings are normalised and
    compared directly because parsing an equation pair back to SymPy is
    unreliable without extra tooling.

    For scalar/expression answers we try a full SymPy symbolic comparison via
    parse_latex (needs antlr4-python3-runtime), then fall back to the
    normalised LaTeX string comparison if that import fails.
    """
    try:
        expected = eval(pr.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307
    except Exception:
        return False

    # Tuple (systems): normalised string comparison is the only practical option
    if isinstance(expected, sympy.Tuple):
        return _normalize_latex(final_answer_latex) == _normalize_latex(pr.answer_latex)

    # Scalar / expression: try symbolic parse
    try:
        from sympy.parsing.latex import parse_latex  # requires antlr4
        got = parse_latex(final_answer_latex)
        if _verify_symbolic(got, expected):
            return True
    except Exception:
        pass

    # Fallback: normalised LaTeX string comparison
    return _normalize_latex(final_answer_latex) == _normalize_latex(pr.answer_latex)


# ---------------------------------------------------------------------------
# Supabase cache helpers
# ---------------------------------------------------------------------------


def _fetch_cached_steps(problem_hash: str) -> StepSolution | None:
    """Return a StepSolution from cache if steps exist and are verified."""
    supabase = get_supabase()
    if supabase is None:
        return None
    try:
        resp = (
            supabase
            .table("problem_cache")
            .select("steps, steps_verified")
            .eq("problem_hash", problem_hash)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        row = rows[0]
        if not row.get("steps_verified") or not row.get("steps"):
            return None
        raw = row["steps"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        return StepSolution(**raw)
    except Exception as exc:
        _LOG.warning("Cache read failed for hash=%s: %s", problem_hash, exc)
        return None


def _store_steps(
    problem_hash: str,
    topic: str,
    pr: ProblemResult,
    solution: StepSolution,
) -> None:
    """Upsert the problem row with verified steps into problem_cache."""
    supabase = get_supabase()
    if supabase is None:
        return
    try:
        supabase.table("problem_cache").upsert({
            "problem_hash": problem_hash,
            "topic": topic,
            "problem_latex": pr.problem_latex,
            "answer_latex": pr.answer_latex,
            "answer_exact": pr.answer_exact,
            "standard_codes": pr.standard_codes,
            "steps": solution.model_dump(),
            "steps_verified": True,
        }).execute()
    except Exception as exc:
        _LOG.error("Failed to write steps to Supabase: %s", exc)


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------


def _build_system_prompt(topic: str, answer_exact: str) -> str:
    method = _METHOD_INSTRUCTIONS.get(topic, "Show your work step by step.")
    return (
        "You are a math teacher writing step-by-step solutions for Algebra 1 students. "
        "Write clear, numbered steps. "
        "Each step has a plain English description and the math expression at that step in LaTeX. "
        f"The final answer MUST equal exactly: {answer_exact}. "
        f"Use the method: {method} "
        'Respond only with valid JSON.'
    )


def _call_gemini(topic: str, pr: ProblemResult) -> dict:
    """Return the raw parsed JSON dict from Gemini 2.5 Flash."""
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai is not installed. "
            "Run: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name=_GEMINI_MODEL,
        system_instruction=_build_system_prompt(topic, pr.answer_exact),
    )
    response = model.generate_content(
        contents=f"Solve this problem step by step: {pr.problem_latex}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    return json.loads(response.text)


# ---------------------------------------------------------------------------
# Problem regeneration
# ---------------------------------------------------------------------------


def _next_problem(topic: str, pr: ProblemResult) -> ProblemResult:
    """Generate the next valid problem by incrementing the seed by 1."""
    instance = TOPIC_REGISTRY[topic]()
    return instance.generate_valid(
        seed=pr.seed_used + 1,
        difficulty=pr.difficulty,
    )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def get_ai_steps(topic: str, problem_result: ProblemResult) -> StepSolution:
    """
    Return AI-generated step-by-step solution for *topic* using Gemini.

    Flow:
      1. Check Supabase cache — return immediately if steps exist and are verified.
      2. Call Gemini; parse and verify the JSON response.
      3. On mismatch: log, increment seed, regenerate problem, retry (max 3 total).
      4. On success: upsert verified steps to Supabase and return StepSolution.

    Raises RuntimeError if all 3 attempts fail to produce a verified answer.
    """
    method_slug = _METHOD_SLUGS.get(topic, topic)
    current_pr = problem_result

    for attempt in range(3):
        cache_hash = _cache_key(topic, current_pr.difficulty, current_pr.seed_used)

        # Only check the cache for the original problem (attempt 0) — retry
        # problems are new seeds that won't be in the cache yet.
        if attempt == 0:
            cached = _fetch_cached_steps(cache_hash)
            if cached is not None:
                return cached

        # Call Gemini
        try:
            raw = _call_gemini(topic, current_pr)
        except Exception as exc:
            _LOG.warning("Gemini call failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                current_pr = _next_problem(topic, current_pr)
            continue

        # Parse the response structure
        try:
            steps = [Step(**s) for s in raw["steps"]]
            final_answer_latex: str = raw["final_answer_latex"]
        except (KeyError, TypeError, ValueError) as exc:
            _LOG.warning(
                "Malformed Gemini response (attempt %d/3): %s — raw=%r",
                attempt + 1, exc, raw,
            )
            if attempt < 2:
                current_pr = _next_problem(topic, current_pr)
            continue

        # Verify the AI's answer matches SymPy's exact answer
        if not _verify_ai_answer(final_answer_latex, current_pr):
            _LOG.warning(
                "Gemini answer mismatch (attempt %d/3): "
                "got final_answer_latex=%r but answer_exact=%r (seed=%d)",
                attempt + 1,
                final_answer_latex,
                current_pr.answer_exact,
                current_pr.seed_used,
            )
            if attempt < 2:
                current_pr = _next_problem(topic, current_pr)
            continue

        # Verified — persist and return
        solution = StepSolution(
            steps=steps,
            final_answer_latex=final_answer_latex,
            method=method_slug,
            verified=True,
        )
        _store_steps(cache_hash, topic, current_pr, solution)
        return solution

    raise RuntimeError(
        f"Gemini failed to produce a verified answer for topic={topic!r} "
        f"after 3 attempts. Last seed tried: {current_pr.seed_used}."
    )


def get_steps(topic: str, problem_result: ProblemResult) -> StepSolution:
    """
    Return step-by-step solution for *problem_result*, preferring scripted steps.

    Tries hand-scripted steps first (always correct, no API call).
    Falls back to Gemini-generated steps for topics not covered by scripted.py.
    """
    scripted = get_scripted_steps(topic, problem_result)
    if scripted is not None:
        return scripted
    return get_ai_steps(topic, problem_result)

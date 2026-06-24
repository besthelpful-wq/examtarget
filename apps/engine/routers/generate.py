import hashlib
import json
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.client import get_supabase
from topics import TOPIC_METADATA, TOPIC_REGISTRY, ProblemResult
from steps.scripted import StepSolution
from steps.ai_steps import get_steps

_LOG = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cache_key(topic: str, difficulty: str, seed: int) -> str:
    """Deterministic SHA-256 cache key for a single problem slot."""
    return hashlib.sha256(f"{topic}:{difficulty}:{seed}".encode()).hexdigest()


def _cached_step_solution(row: dict) -> StepSolution | None:
    """Reconstruct a StepSolution from a cache row that already has verified steps."""
    if not row.get("steps_verified") or not row.get("steps"):
        return None
    raw = row["steps"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    try:
        return StepSolution(**raw)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ProblemResultWithSteps(ProblemResult):
    """ProblemResult extended with an optional verified step solution."""
    step_solution: StepSolution | None = None


class GenerateRequest(BaseModel):
    topic: str
    difficulty: Literal["easy", "medium", "hard"]
    count: int = Field(ge=1, le=40)
    seed: int
    version: int = Field(default=1, ge=1)
    include_steps: bool = False


class GenerateResponse(BaseModel):
    topic: str
    difficulty: str
    version: int
    seed: int
    problems: list[ProblemResultWithSteps]


class TopicInfo(BaseModel):
    slug: str
    display_name: str
    standard_codes: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/topics", response_model=list[TopicInfo])
def list_topics() -> list[TopicInfo]:
    return [
        TopicInfo(slug=slug, display_name=str(meta["display_name"]), standard_codes=list(meta["standard_codes"]))  # type: ignore[arg-type]
        for slug, meta in TOPIC_METADATA.items()
    ]


@router.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateRequest) -> GenerateResponse:
    if body.topic not in TOPIC_REGISTRY:
        valid = ", ".join(TOPIC_REGISTRY)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic '{body.topic}'. Valid topics: {valid}",
        )

    # Pre-compute every (effective_seed, cache_hash) pair for this request.
    slots: list[tuple[int, str]] = []
    for i in range(body.count):
        effective_seed = body.seed + i + body.version * 10_000
        slots.append((effective_seed, _cache_key(body.topic, body.difficulty, effective_seed)))

    all_hashes = [h for _, h in slots]

    # Batched cache lookup (skipped when Supabase is not configured).
    supabase = get_supabase()
    cache_map: dict[str, dict] = {}
    if supabase is not None:
        cached_rows = (
            supabase.table("problem_cache")
            .select("problem_hash, problem_latex, answer_latex, answer_exact, standard_codes, steps, steps_verified")
            .in_("problem_hash", all_hashes)
            .execute()
        )
        cache_map = {row["problem_hash"]: row for row in (cached_rows.data or [])}

    topic_instance = TOPIC_REGISTRY[body.topic]()
    problems: list[ProblemResultWithSteps] = []
    to_insert: list[dict] = []

    for effective_seed, cache_hash in slots:
        if cache_hash in cache_map:
            _LOG.info("CACHE HIT: %s", cache_hash)
            row = cache_map[cache_hash]
            result = ProblemResultWithSteps(
                problem_latex=row["problem_latex"],
                answer_latex=row["answer_latex"],
                answer_exact=row["answer_exact"],
                seed_used=effective_seed,
                difficulty=body.difficulty,
                standard_codes=row["standard_codes"] or [],
                # Use cached verified steps immediately — no API call needed.
                step_solution=_cached_step_solution(row) if body.include_steps else None,
            )
        else:
            _LOG.info("CACHE MISS: %s", cache_hash)
            try:
                pr = topic_instance.generate_valid(
                    seed=effective_seed,
                    difficulty=body.difficulty,
                )
            except ValueError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            result = ProblemResultWithSteps(**pr.model_dump())
            to_insert.append({
                "problem_hash": cache_hash,
                "topic": body.topic,
                "problem_latex": pr.problem_latex,
                "answer_latex": pr.answer_latex,
                "answer_exact": pr.answer_exact,
                "standard_codes": pr.standard_codes,
            })

        # Call get_steps() only when needed: steps requested AND not already
        # satisfied from the cache above.
        if body.include_steps and result.step_solution is None:
            try:
                result.step_solution = get_steps(body.topic, result)
            except Exception as exc:
                _LOG.warning(
                    "get_steps failed for topic=%s seed=%d: %s",
                    body.topic, effective_seed, exc,
                )

        problems.append(result)

    # Batched insert for all cache misses (skipped without Supabase).
    if to_insert and supabase is not None:
        supabase.table("problem_cache").insert(to_insert).execute()

    return GenerateResponse(
        topic=body.topic,
        difficulty=body.difficulty,
        version=body.version,
        seed=body.seed,
        problems=problems,
    )

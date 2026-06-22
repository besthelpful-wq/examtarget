import hashlib
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.client import get_supabase
from topics import TOPIC_METADATA, TOPIC_REGISTRY, ProblemResult

router = APIRouter(tags=["generate"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cache_key(topic: str, difficulty: str, seed: int) -> str:
    """Deterministic SHA-256 cache key for a single problem slot."""
    return hashlib.sha256(f"{topic}:{difficulty}:{seed}".encode()).hexdigest()


def _row_to_result(row: dict, seed: int, difficulty: str) -> ProblemResult:
    return ProblemResult(
        problem_latex=row["problem_latex"],
        answer_latex=row["answer_latex"],
        answer_exact=row["answer_exact"],
        seed_used=seed,
        difficulty=difficulty,
        standard_codes=row["standard_codes"] or [],
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    topic: str
    difficulty: Literal["easy", "medium", "hard"]
    count: int = Field(ge=1, le=40)
    seed: int
    version: int = Field(default=1, ge=1)


class GenerateResponse(BaseModel):
    topic: str
    difficulty: str
    version: int
    seed: int
    problems: list[ProblemResult]


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

    # Single batched cache lookup — avoids N round-trips for N problems.
    supabase = get_supabase()
    cached_rows = (
        supabase.table("problem_cache")
        .select("problem_hash, problem_latex, answer_latex, answer_exact, standard_codes")
        .in_("problem_hash", all_hashes)
        .execute()
    )
    cache_map: dict[str, dict] = {row["problem_hash"]: row for row in (cached_rows.data or [])}

    topic_instance = TOPIC_REGISTRY[body.topic]()
    problems: list[ProblemResult] = []
    to_insert: list[dict] = []

    for effective_seed, cache_hash in slots:
        if cache_hash in cache_map:
            result = _row_to_result(cache_map[cache_hash], effective_seed, body.difficulty)
        else:
            try:
                result = topic_instance.generate_valid(
                    seed=effective_seed,
                    difficulty=body.difficulty,
                )
            except ValueError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            to_insert.append({
                "problem_hash": cache_hash,
                "topic": body.topic,
                "problem_latex": result.problem_latex,
                "answer_latex": result.answer_latex,
                "answer_exact": result.answer_exact,
                "standard_codes": result.standard_codes,
            })

        problems.append(result)

    # Single batched insert for all cache misses.
    if to_insert:
        supabase.table("problem_cache").insert(to_insert).execute()

    return GenerateResponse(
        topic=body.topic,
        difficulty=body.difficulty,
        version=body.version,
        seed=body.seed,
        problems=problems,
    )

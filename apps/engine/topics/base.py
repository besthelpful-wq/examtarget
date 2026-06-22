import math
from abc import ABC, abstractmethod

import sympy
from pydantic import BaseModel

# SymPy namespace used to reconstruct expressions from srepr strings.
# eval() is intentional here — srepr() produces constructor call syntax
# (e.g. "Rational(3, 4)") that round-trips safely inside this namespace.
_SYMPY_NS: dict = {k: v for k, v in sympy.__dict__.items() if not k.startswith("_")}

# Denominator cleanliness limits per difficulty level.
# Hard difficulty imposes no limit.
_DENOM_LIMITS: dict[str, int] = {"easy": 20, "medium": 50}


class ProblemResult(BaseModel):
    problem_latex: str
    answer_latex: str
    answer_exact: str       # sympy.srepr() — round-trips to exact SymPy expression
    seed_used: int
    difficulty: str         # 'easy' | 'medium' | 'hard' — needed by validate()
    standard_codes: list[str]


class TopicTemplate(ABC):

    @abstractmethod
    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        """Produce one problem for the given seed and difficulty level.

        Must always return a result (even if degenerate); validation is
        handled by validate() / generate_valid().
        """

    def validate(self, result: ProblemResult) -> bool:
        """Return True only if the result is clean enough to show a student.

        Rejects:
          - Non-finite or complex answers (infinity, NaN, imaginary part).
          - Rational answers whose denominator exceeds the difficulty limit
            (easy ≤ 20, medium ≤ 50; hard is unconstrained).
          - Any answer_exact string that raises an exception when reconstructed
            or numerically evaluated — catches malformed srepr, SymPy errors, etc.
        """
        try:
            expr = eval(result.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307

            # Symbolic finiteness check (fast path).
            if expr.is_finite is False or expr.is_real is False:
                return False

            # Numerical evaluation — catches cases SymPy cannot determine
            # symbolically (is_finite == None) and any complex residual.
            num = complex(expr.evalf())
            if math.isnan(num.real) or math.isinf(num.real) or num.imag != 0:
                return False

            # Denominator cleanliness — only for Rational non-integers.
            limit = _DENOM_LIMITS.get(result.difficulty)
            if limit is not None:
                if isinstance(expr, sympy.Rational) and not isinstance(expr, sympy.Integer):
                    if abs(expr.q) > limit:
                        return False

        except Exception:
            return False

        return True

    def generate_valid(
        self,
        seed: int,
        difficulty: str,
        max_attempts: int = 20,
    ) -> ProblemResult:
        """Call generate() in a loop, incrementing seed on each failure.

        Raises ValueError if no clean problem is found within max_attempts.
        """
        for offset in range(max_attempts):
            result = self.generate(seed + offset, difficulty)
            if self.validate(result):
                return result

        raise ValueError(
            f"{self.__class__.__name__}: could not produce a valid '{difficulty}' problem "
            f"after {max_attempts} attempts (seeds {seed}–{seed + max_attempts - 1})."
        )

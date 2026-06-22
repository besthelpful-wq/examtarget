import random

import sympy

from .base import ProblemResult, TopicTemplate

_CODES = ["CCSS.MATH.CONTENT.HSA-SSE.B.3"]

_SQUARE_FREE = [2, 3, 5, 6, 7, 10, 11, 13, 15, 17]

# (base, root) pairs where base^(1/root) is a positive integer.
_PERFECT_POWERS = [
    (8, 3), (16, 4), (27, 3), (32, 5), (64, 3), (64, 6),
]


class ExponentsAndRadicals(TopicTemplate):

    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        rng = random.Random(seed)

        if difficulty == "easy":
            return self._radical_simplify(rng, seed, difficulty)
        elif difficulty == "medium":
            fn = rng.choice([self._product_of_powers, self._power_of_power])
            return fn(rng, seed, difficulty)
        else:
            fn = rng.choice([self._rational_exponent, self._radical_simplify])
            return fn(rng, seed, difficulty)

    # ------------------------------------------------------------------
    # Problem builders
    # ------------------------------------------------------------------

    def _radical_simplify(
        self, rng: random.Random, seed: int, difficulty: str
    ) -> ProblemResult:
        coeff = rng.choice([3, 4, 5, 6] if difficulty == "hard" else [2, 3, 4, 5])
        radicand_factor = rng.choice(_SQUARE_FREE)
        n = coeff * coeff * radicand_factor      # e.g. 48 = 4²·3
        answer = sympy.sqrt(n)                   # SymPy auto-simplifies: 4√3
        return ProblemResult(
            problem_latex=rf"\sqrt{{{n}}}",
            answer_latex=sympy.latex(answer),
            answer_exact=sympy.srepr(answer),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def _product_of_powers(
        self, rng: random.Random, seed: int, difficulty: str
    ) -> ProblemResult:
        base = rng.choice([2, 3, 4, 5])
        m = rng.randint(2, 6)
        n = rng.randint(1, 4)
        answer = sympy.Integer(base) ** (m + n)
        return ProblemResult(
            problem_latex=rf"{base}^{{{m}}} \cdot {base}^{{{n}}}",
            answer_latex=sympy.latex(answer),
            answer_exact=sympy.srepr(answer),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def _power_of_power(
        self, rng: random.Random, seed: int, difficulty: str
    ) -> ProblemResult:
        base = rng.choice([2, 3, 4])
        m = rng.randint(2, 4)
        n = rng.randint(2, 3)
        answer = sympy.Integer(base) ** (m * n)
        return ProblemResult(
            problem_latex=rf"\left({base}^{{{m}}}\right)^{{{n}}}",
            answer_latex=sympy.latex(answer),
            answer_exact=sympy.srepr(answer),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def _rational_exponent(
        self, rng: random.Random, seed: int, difficulty: str
    ) -> ProblemResult:
        base, root = rng.choice(_PERFECT_POWERS)
        # numerator strictly less than root so the exponent stays < 1 in display
        p = rng.randint(2, root - 1) if root > 2 else 1
        answer = sympy.Integer(base) ** sympy.Rational(p, root)
        problem_latex = (
            rf"\sqrt[{root}]{{{base}}}"
            if p == 1
            else rf"{base}^{{\frac{{{p}}}{{{root}}}}}"
        )
        return ProblemResult(
            problem_latex=problem_latex,
            answer_latex=sympy.latex(answer),
            answer_exact=sympy.srepr(answer),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

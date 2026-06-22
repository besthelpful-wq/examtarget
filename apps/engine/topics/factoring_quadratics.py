import random

import sympy

from .base import ProblemResult, TopicTemplate, _SYMPY_NS

_CODES = [
    "CCSS.MATH.CONTENT.HSA-SSE.B.3",
    "CCSS.MATH.CONTENT.HSA-APR.B.3",
]
_X = sympy.Symbol("x")


class FactoringQuadratics(TopicTemplate):

    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        rng = random.Random(seed)

        if difficulty == "easy":
            r1 = rng.randint(-5, 5)
            r2 = rng.randint(-5, 5)
            a = 1
        elif difficulty == "medium":
            r1 = rng.randint(-8, 8)
            r2 = rng.randint(-8, 8)
            a = 1
        else:  # hard
            r1 = rng.randint(-5, 5)
            r2 = rng.randint(-5, 5)
            a = rng.choice([1, 2, 3])

        # Build from integer roots: a(x − r1)(x − r2)
        factored_raw = sympy.Integer(a) * (_X - r1) * (_X - r2)
        expanded = sympy.expand(factored_raw)

        # sympy.factor() gives the canonical form and double-checks factorability.
        factored = sympy.factor(expanded)

        return ProblemResult(
            problem_latex=sympy.latex(expanded),
            answer_latex=sympy.latex(factored),
            answer_exact=sympy.srepr(factored),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def validate(self, result: ProblemResult) -> bool:
        try:
            expr = eval(result.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307
            poly = sympy.Poly(sympy.expand(expr), _X)
            if poly.degree() != 2:
                return False
            roots = sympy.roots(poly)
            if not roots:
                return False
            if not all(r.is_rational for r in roots):
                return False
            # Reject x² — both roots zero is too trivial.
            if all(r == 0 for r in roots):
                return False
            return True
        except Exception:
            return False

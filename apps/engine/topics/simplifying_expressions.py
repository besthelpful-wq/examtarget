import random

import sympy

from .base import ProblemResult, TopicTemplate, _SYMPY_NS

_CODES = ["CCSS.MATH.CONTENT.HSA-SSE.A.1"]
_X = sympy.Symbol("x")


def _extra_latex(expr: sympy.Expr) -> str:
    """Return ' + latex' or ' - latex' for an additive extra term."""
    s = sympy.latex(expr)
    if s.startswith("-"):
        return f" - {s[1:].strip()}"
    return f" + {s}"


class SimplifyingExpressions(TopicTemplate):

    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        rng = random.Random(seed)

        if difficulty == "easy":
            # Combine like terms: ax + bx + c
            a = rng.randint(2, 8)
            b = rng.randint(2, 8)
            c = rng.randint(-12, 12)

            c_str = f" + {c}" if c > 0 else (f" - {abs(c)}" if c < 0 else "")
            problem_latex = f"{a}x + {b}x{c_str}"
            simplified = sympy.expand(a * _X + b * _X + c)

        elif difficulty == "medium":
            # Distribute and collect: a(bx + c) + d(ex + f)
            a = rng.randint(2, 5)
            b = rng.randint(1, 5)
            c = rng.randint(-8, 8)
            d = rng.randint(2, 5)
            e = rng.randint(1, 5)
            f = rng.randint(-8, 8)

            inner1 = b * _X + c
            inner2 = e * _X + f
            problem_latex = (
                rf"{a}\left({sympy.latex(inner1)}\right)"
                rf" + {d}\left({sympy.latex(inner2)}\right)"
            )
            simplified = sympy.collect(sympy.expand(a * inner1 + d * inner2), _X)

        else:  # hard
            # Expand: (ax + b)(cx + d) + extra
            a = rng.randint(1, 4)
            b = rng.randint(-6, 6)
            c = rng.randint(1, 4)
            d = rng.randint(-6, 6)
            e = rng.randint(-8, 8)
            f_c = rng.randint(-12, 12)

            b1 = a * _X + b
            b2 = c * _X + d
            extra = e * _X + f_c
            problem_latex = (
                rf"\left({sympy.latex(b1)}\right)"
                rf"\left({sympy.latex(b2)}\right)"
            )
            if e != 0 or f_c != 0:
                problem_latex += _extra_latex(extra)
            simplified = sympy.expand(b1 * b2 + extra)

        return ProblemResult(
            problem_latex=problem_latex,
            answer_latex=sympy.latex(simplified),
            answer_exact=sympy.srepr(simplified),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def validate(self, result: ProblemResult) -> bool:
        try:
            expr = eval(result.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307
            if not expr.free_symbols:
                return False
            poly = sympy.Poly(sympy.expand(expr), _X)
            if poly.degree() < 1:
                return False
            for coeff in poly.all_coeffs():
                if not coeff.is_Integer or abs(int(coeff)) > 500:
                    return False
            return True
        except Exception:
            return False

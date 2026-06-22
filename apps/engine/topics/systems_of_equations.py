import math
import random

import sympy

from .base import ProblemResult, TopicTemplate, _DENOM_LIMITS, _SYMPY_NS

_CODES = ["CCSS.MATH.CONTENT.HSA-REI.C.6"]
_X, _Y = sympy.symbols("x y")


class SystemsOfEquations(TopicTemplate):

    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        rng = random.Random(seed)

        if difficulty == "easy":
            sol_range, coeff_lim = 5, 3
        elif difficulty == "medium":
            sol_range, coeff_lim = 10, 5
        else:
            sol_range, coeff_lim = 15, 8

        # Fix integer solutions first, then build the system around them so
        # the answer is always a clean integer pair.
        x0 = rng.randint(-sol_range, sol_range)
        y0 = rng.randint(-sol_range, sol_range)

        a = rng.randint(1, coeff_lim)
        b = rng.randint(-coeff_lim, coeff_lim)

        # Find d, e with non-zero determinant (a*e - b*d ≠ 0).
        d, e = 0, 1
        for _ in range(20):
            d = rng.randint(-coeff_lim, coeff_lim)
            e = rng.randint(1, coeff_lim)
            if a * e - b * d != 0:
                break

        c = a * x0 + b * y0
        f = d * x0 + e * y0

        sol = sympy.solve([a * _X + b * _Y - c, d * _X + e * _Y - f], [_X, _Y])
        x_sol = sol.get(_X, sympy.Integer(x0))
        y_sol = sol.get(_Y, sympy.Integer(y0))

        eq1 = rf"{sympy.latex(a * _X + b * _Y)} = {c}"
        eq2 = rf"{sympy.latex(d * _X + e * _Y)} = {f}"

        return ProblemResult(
            problem_latex=rf"\begin{{cases}} {eq1} \\ {eq2} \end{{cases}}",
            answer_latex=rf"x = {sympy.latex(x_sol)},\quad y = {sympy.latex(y_sol)}",
            answer_exact=sympy.srepr(sympy.Tuple(x_sol, y_sol)),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

    def validate(self, result: ProblemResult) -> bool:
        try:
            expr = eval(result.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307
            limit = _DENOM_LIMITS.get(result.difficulty)
            for val in expr:
                if val.is_finite is False or val.is_real is False:
                    return False
                num = complex(val.evalf())
                if math.isnan(num.real) or math.isinf(num.real) or num.imag != 0:
                    return False
                if limit and isinstance(val, sympy.Rational) and not isinstance(val, sympy.Integer):
                    if abs(val.q) > limit:
                        return False
        except Exception:
            return False
        return True

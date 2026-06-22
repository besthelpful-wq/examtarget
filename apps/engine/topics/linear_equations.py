import random

import sympy

from .base import ProblemResult, TopicTemplate

_CODES = ["CCSS.MATH.CONTENT.HSA-REI.B.3"]


class LinearEquations(TopicTemplate):

    def generate(self, seed: int, difficulty: str) -> ProblemResult:
        rng = random.Random(seed)

        if difficulty == "easy":
            a = rng.randint(1, 5)
            b = rng.randint(-10, 10)
            c = rng.randint(-10, 10)
        elif difficulty == "medium":
            a = rng.randint(1, 10)
            b = rng.randint(-20, 20)
            c = rng.randint(-20, 20)
        else:  # hard
            a = rng.choice([i for i in range(-20, 21) if i != 0])
            b = rng.randint(-50, 50)
            c = rng.randint(-50, 50)

        x = sympy.Symbol("x")
        lhs = a * x + b
        solution = sympy.Rational(c - b, a)

        return ProblemResult(
            problem_latex=rf"{sympy.latex(lhs)} = {c}",
            answer_latex=rf"x = {sympy.latex(solution)}",
            answer_exact=sympy.srepr(solution),
            seed_used=seed,
            difficulty=difficulty,
            standard_codes=_CODES,
        )

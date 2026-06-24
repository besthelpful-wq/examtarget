from __future__ import annotations

import sympy
from pydantic import BaseModel
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from topics.base import ProblemResult, _SYMPY_NS

_X = sympy.Symbol("x")
_PARSE_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


class Step(BaseModel):
    description: str
    math_latex: str


class StepSolution(BaseModel):
    steps: list[Step]
    final_answer_latex: str
    method: str
    verified: bool = True


def _parse_lhs(s: str) -> sympy.Expr:
    """Parse a SymPy-generated linear expression string (implicit multiplication, no antlr4)."""
    return parse_expr(s, local_dict={"x": _X}, transformations=_PARSE_TRANSFORMS)


def _term_abs(coeff: int, var: str) -> str | None:
    """Return |coeff|*var as a bare string (no leading sign). None if coeff == 0."""
    if coeff == 0:
        return None
    c = abs(coeff)
    if var:
        return var if c == 1 else f"{c} {var}"
    return str(c)


def _poly4_latex(a: int, p: int, q: int, c: int) -> str:
    """
    Render ax^2 + px + qx + c as LaTeX keeping the two middle terms separate
    so students can see the split before grouping.
    """
    entries = [(a, "x^{2}"), (p, "x"), (q, "x"), (c, "")]
    parts: list[tuple[bool, str]] = []
    for coeff, var in entries:
        s = _term_abs(coeff, var)
        if s is not None:
            parts.append((coeff < 0, s))

    if not parts:
        return "0"

    neg0, s0 = parts[0]
    result = f"-{s0}" if neg0 else s0
    for neg, s in parts[1:]:
        result += f" - {s}" if neg else f" + {s}"
    return result


# ---------------------------------------------------------------------------
# linear_equations
# ---------------------------------------------------------------------------

def _steps_linear_equations(pr: ProblemResult) -> StepSolution | None:
    try:
        lhs_str, rhs_str = pr.problem_latex.split(" = ", 1)
        lhs = _parse_lhs(lhs_str)
        c = sympy.Integer(int(rhs_str.strip()))
        poly = sympy.Poly(lhs, _X)
        a = poly.nth(1)  # coefficient of x
        b = poly.nth(0)  # constant term
    except Exception:
        return None

    steps: list[Step] = [
        Step(
            description="Write the original equation.",
            math_latex=pr.problem_latex,
        )
    ]

    # Step 2 — eliminate the constant b (if present)
    if b != 0:
        b_abs = abs(int(b))
        desc = f"Subtract {b_abs} from both sides." if b > 0 else f"Add {b_abs} to both sides."
        current_rhs = c - b
        steps.append(Step(
            description=desc,
            math_latex=rf"{sympy.latex(a * _X)} = {sympy.latex(current_rhs)}",
        ))
    else:
        current_rhs = c

    # Step 3 — divide by a (if a ≠ 1)
    if a != 1:
        solution = sympy.Rational(int(current_rhs), int(a))
        steps.append(Step(
            description=f"Divide both sides by {int(a)}.",
            math_latex=rf"x = {sympy.latex(solution)}",
        ))

    # Step 4 — state the solution
    steps.append(Step(
        description="State the solution.",
        math_latex=pr.answer_latex,
    ))

    return StepSolution(
        steps=steps,
        final_answer_latex=pr.answer_latex,
        method="isolation",
        verified=True,
    )


# ---------------------------------------------------------------------------
# factoring_quadratics
# ---------------------------------------------------------------------------

def _steps_factoring_quadratics(pr: ProblemResult) -> StepSolution | None:
    try:
        factored = eval(pr.answer_exact, {"__builtins__": {}}, _SYMPY_NS)  # noqa: S307
        expanded = sympy.expand(factored)
        poly = sympy.Poly(expanded, _X)
        a_coef = int(poly.nth(2))
        b_coef = int(poly.nth(1))
        c_coef = int(poly.nth(0))
    except Exception:
        return None

    steps: list[Step] = [
        Step(
            description="Write the original expression.",
            math_latex=pr.problem_latex,
        )
    ]

    # Special case: one root is zero (c = 0) — factor out x directly
    if c_coef == 0:
        gcf = int(sympy.gcd(sympy.Integer(a_coef), sympy.Integer(b_coef)))
        a_inner = a_coef // gcf
        b_inner = b_coef // gcf
        inner_latex = sympy.latex(sympy.Integer(a_inner) * _X + sympy.Integer(b_inner))

        if gcf == 1:
            steps.append(Step(
                description="Factor out x from every term.",
                math_latex=rf"x \left( {inner_latex} \right)",
            ))
        else:
            steps.append(Step(
                description=f"Factor out {gcf}x from every term.",
                math_latex=rf"{gcf} x \left( {inner_latex} \right)",
            ))

        steps.append(Step(
            description="Write the fully factored form.",
            math_latex=pr.answer_latex,
        ))

        return StepSolution(
            steps=steps,
            final_answer_latex=pr.answer_latex,
            method="factoring",
            verified=True,
        )

    # General case — AC method (factor by grouping)
    try:
        roots_dict = sympy.roots(poly)
        root_list: list[sympy.Expr] = []
        for r, mult in roots_dict.items():
            root_list.extend([r] * int(mult))
        if len(root_list) < 2:
            return None
    except Exception:
        return None

    r1, r2 = root_list[0], root_list[1]

    # p = -a*r1, q = -a*r2 so that p*q = a*c and p+q = b
    p = int(-sympy.Integer(a_coef) * r1)
    q = int(-sympy.Integer(a_coef) * r2)
    if p * q != a_coef * c_coef or p + q != b_coef:
        p, q = q, p
        if p * q != a_coef * c_coef or p + q != b_coef:
            return None

    ac_product = a_coef * c_coef

    # Step 2 — find the two numbers
    steps.append(Step(
        description=(
            f"Find two numbers that multiply to a*c = {a_coef}*{c_coef} = {ac_product} "
            f"and add to b = {b_coef}. "
            f"The numbers are {p} and {q}."
        ),
        math_latex=rf"{p} \times {q} = {ac_product}, \quad {p} + {q} = {b_coef}",
    ))

    # Step 3 — rewrite the middle term as p*x + q*x
    steps.append(Step(
        description=f"Rewrite the middle term {b_coef}x as {p}x + {q}x.",
        math_latex=_poly4_latex(a_coef, p, q, c_coef),
    ))

    # Step 4 — factor by grouping
    # (ax² + px) + (qx + c) = x(ax + p) + k(ax + p), where k = c // p
    k = c_coef // p
    inner_bi_latex = sympy.latex(sympy.Integer(a_coef) * _X + sympy.Integer(p))
    x_grp = rf"x \left( {inner_bi_latex} \right)"
    k_abs = abs(k)
    k_grp = (
        rf"\left( {inner_bi_latex} \right)"
        if k_abs == 1
        else rf"{k_abs} \left( {inner_bi_latex} \right)"
    )
    grouping_latex = f"{x_grp} {'+ ' if k >= 0 else '- '}{k_grp}"

    steps.append(Step(
        description="Group the first two terms and the last two terms, then factor each group.",
        math_latex=grouping_latex,
    ))

    # Step 5 — factored form
    steps.append(Step(
        description="Factor out the common binomial to write the fully factored form.",
        math_latex=pr.answer_latex,
    ))

    return StepSolution(
        steps=steps,
        final_answer_latex=pr.answer_latex,
        method="factoring",
        verified=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def get_scripted_steps(topic: str, problem_result: ProblemResult) -> StepSolution | None:
    if topic == "linear_equations":
        return _steps_linear_equations(problem_result)
    if topic == "factoring_quadratics":
        return _steps_factoring_quadratics(problem_result)
    return None

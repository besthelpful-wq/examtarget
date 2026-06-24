"""
PDF export route.

Rendering pipeline:
  LaTeX string → matplotlib mathtext → PNG bytes → embedded in fpdf2 PDF

matplotlib mathtext handles the vast majority of our LaTeX output (fractions,
roots, superscripts, subscripts).  \begin{cases} environments (systems of
equations) are split into individual lines before rendering.
"""

import io
import re
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(tags=["export"])


# ─── Request model ────────────────────────────────────────────────────────────

class StepInput(BaseModel):
    description: str
    math_latex: str


class StepSolutionInput(BaseModel):
    steps: list[StepInput]
    final_answer_latex: str
    method: str
    verified: bool = True


class ProblemInput(BaseModel):
    problem_latex: str
    answer_latex: str
    seed_used: int
    difficulty: str
    standard_codes: list[str]
    step_solution: StepSolutionInput | None = None


class ExportPDFRequest(BaseModel):
    topic: str
    difficulty: str
    seed: int
    version: int
    problems: list[ProblemInput]
    include_answer_key: bool
    include_steps: bool = False
    steps_placement: Literal["inline", "separate_page"] = "inline"
    title: str = "Worksheet"
    teacher_name: str = ""
    class_period: str = ""
    date: str = ""


# ─── Math rendering ───────────────────────────────────────────────────────────

_CASES_RE = re.compile(r'\\begin\{cases\}(.+?)\\end\{cases\}', re.DOTALL)
_PNG_CACHE: dict[tuple[str, float], bytes] = {}


def _math_to_lines(latex: str) -> list[str]:
    """Split \\begin{cases} into individual equation strings; otherwise [latex]."""
    m = _CASES_RE.search(latex)
    if m:
        inner = m.group(1)
        return [
            ln.strip().rstrip("\\").strip()
            for ln in inner.split(r"\\")
            if ln.strip().rstrip("\\").strip()
        ]
    return [latex]


def _render_math_png(latex: str, fontsize: float = 13.0) -> bytes:
    """
    Render a LaTeX math expression to PNG (white background, 150 dpi).
    Cached per (latex, fontsize) pair to avoid re-rendering on the same request.
    """
    key = (latex, fontsize)
    if key in _PNG_CACHE:
        return _PNG_CACHE[key]

    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(7, 0.6))
    FigureCanvasAgg(fig)          # required to init the Agg canvas
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.text(
        0.01, 0.5,
        f"${latex}$",
        fontsize=fontsize,
        va="center", ha="left",
        transform=ax.transAxes,
        usetex=False,
    )
    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=150,
        bbox_inches="tight", facecolor="white",
        edgecolor="none", pad_inches=0.04,
    )
    buf.seek(0)
    result = buf.read()
    _PNG_CACHE[key] = result
    return result


# ─── Layout constants (mm) ───────────────────────────────────────────────────

_MARGIN   = 25.4          # 1 inch
_CW       = 215.9 - 2 * _MARGIN   # content width  ≈ 165.1 mm
_NUM_W    = 8.0           # number column width
_WORK_H   = 30.0          # work-space height (≈ 3 cm)
_ROW_H    = 12.0          # answer-key row height
_STEP_IMG_W = min(_CW - 16, 110.0)   # max width for step math images
_STEP_IMG_H = 8.5                     # assumed rendered height per math line


# ─── Header ──────────────────────────────────────────────────────────────────

def _draw_header(pdf: object, title: str, teacher: str, period: str, date: str) -> None:
    from fpdf import FPDF
    assert isinstance(pdf, FPDF)

    y0 = pdf.get_y()

    # Title (left half)
    pdf.set_font("Times", style="B", size=14)
    pdf.set_xy(_MARGIN, y0)
    pdf.cell(_CW * 0.55, 7, title, align="L")

    # Meta fields (right half): Name / Period + Date
    mx = _MARGIN + _CW * 0.57
    mw = _CW * 0.43

    def _field(label: str, value: str, x: float, y: float, w: float) -> None:
        assert isinstance(pdf, FPDF)
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_xy(x, y)
        pdf.cell(13, 5, label + ":", align="L")
        fx = pdf.get_x()
        if value:
            pdf.cell(w - 13, 5, value)
        else:
            pdf.line(fx + 1, y + 4.5, x + w, y + 4.5)

    _field("Name",   teacher, mx,      y0,     mw)
    _field("Period", period,  mx,      y0 + 6, mw * 0.45)
    _field("Date",   date,    mx + mw * 0.48, y0 + 6, mw * 0.52)

    # Rule
    ry = y0 + 14
    pdf.set_line_width(0.4)
    pdf.set_draw_color(0, 0, 0)
    pdf.line(_MARGIN, ry, _MARGIN + _CW, ry)
    pdf.set_line_width(0.2)
    pdf.set_y(ry + 4)


# ─── Step solution rendering ──────────────────────────────────────────────────

def _draw_step_solution(pdf: object, solution: StepSolutionInput) -> None:
    """
    Draw step-by-step solution at the current y position.
    Uses relative positioning so auto-page-break handles overflow.
    """
    from fpdf import FPDF
    assert isinstance(pdf, FPDF)

    # "Solution" label
    pdf.set_font("Helvetica", style="I", size=8.5)
    pdf.set_text_color(90, 60, 180)
    pdf.set_xy(_MARGIN, pdf.get_y() + 1)
    pdf.cell(_CW, 4.5, "Solution:", ln=True)
    pdf.set_text_color(0, 0, 0)

    for i, step in enumerate(solution.steps, 1):
        # Step number + description text
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_xy(_MARGIN + 4, pdf.get_y())
        label = f"{i}.  "
        full_text = label + step.description
        pdf.multi_cell(_CW - 4, 4.5, full_text, align="L")

        # Step math expression
        try:
            png = _render_math_png(step.math_latex, fontsize=10.5)
            img_y = pdf.get_y()
            pdf.image(io.BytesIO(png), x=_MARGIN + 14, y=img_y, w=_STEP_IMG_W)
            pdf.set_y(img_y + _STEP_IMG_H)
        except Exception:
            pdf.set_font("Courier", size=8.5)
            pdf.set_xy(_MARGIN + 14, pdf.get_y())
            pdf.cell(_CW - 14, 4.5, step.math_latex[:70], ln=True)

        pdf.ln(0.5)

    pdf.ln(2)


# ─── Problems page ────────────────────────────────────────────────────────────

def _draw_problems(
    pdf: object,
    problems: list[ProblemInput],
    include_steps_inline: bool = False,
) -> None:
    from fpdf import FPDF
    assert isinstance(pdf, FPDF)

    eq_x  = _MARGIN + _NUM_W + 1
    eq_mw = _CW - _NUM_W - 1          # max equation image width
    img_w = min(eq_mw, 120.0)         # cap at 120 mm

    for i, p in enumerate(problems, 1):
        lines = _math_to_lines(p.problem_latex)
        py = pdf.get_y()

        # Problem number
        pdf.set_font("Times", style="B", size=11)
        pdf.set_xy(_MARGIN, py)
        pdf.cell(_NUM_W, 7, f"{i}.", align="R")

        # Equation line(s)
        ey = py
        for line_latex in lines:
            try:
                png = _render_math_png(line_latex)
                pdf.image(io.BytesIO(png), x=eq_x, y=ey, w=img_w)
                ey += 8.5
            except Exception:
                pdf.set_font("Courier", size=10)
                pdf.set_xy(eq_x, ey)
                pdf.cell(eq_mw, 7, line_latex[:80])
                ey += 7

        after_eq_y = max(py + 11, ey + 2)
        pdf.set_y(after_eq_y)

        if include_steps_inline and p.step_solution:
            # Steps replace the blank work space
            _draw_step_solution(pdf, p.step_solution)
        else:
            # Blank work space for student
            pdf.ln(_WORK_H)

        rule_y = pdf.get_y()
        pdf.set_draw_color(200, 200, 200)
        pdf.line(_MARGIN, rule_y, _MARGIN + _CW, rule_y)
        pdf.set_draw_color(0, 0, 0)
        pdf.ln(2)


# ─── Answer-key page ─────────────────────────────────────────────────────────

def _draw_answers(pdf: object, problems: list[ProblemInput]) -> None:
    from fpdf import FPDF
    assert isinstance(pdf, FPDF)

    col_w = (_CW - 6) / 2             # two columns with 6 mm gap
    lx    = _MARGIN                   # left column x
    rx    = _MARGIN + col_w + 6       # right column x
    ans_w = col_w - _NUM_W - 2        # image width within a column

    start_y = pdf.get_y()
    n = len(problems)
    rows = (n + 1) // 2

    for row in range(rows):
        y = start_y + row * _ROW_H

        for col, idx in enumerate((row * 2, row * 2 + 1)):
            if idx >= n:
                continue
            p   = problems[idx]
            cx  = lx if col == 0 else rx
            pdf.set_font("Times", style="B", size=10)
            pdf.set_xy(cx, y)
            pdf.cell(_NUM_W, 6, f"{idx + 1}.", align="R")
            try:
                png = _render_math_png(p.answer_latex, fontsize=11.0)
                pdf.image(io.BytesIO(png), x=cx + _NUM_W + 1, y=y, w=ans_w)
            except Exception:
                pdf.set_font("Courier", size=9)
                pdf.set_xy(cx + _NUM_W + 1, y)
                pdf.cell(ans_w, 6, p.answer_latex[:45])

    pdf.set_y(start_y + rows * _ROW_H + 4)


# ─── Separate solutions page ─────────────────────────────────────────────────

def _draw_solutions_page(pdf: object, problems: list[ProblemInput]) -> None:
    """Add a new page with full step-by-step solutions for every problem."""
    from fpdf import FPDF
    assert isinstance(pdf, FPDF)

    pdf.add_page()

    # Page title
    pdf.set_font("Times", style="B", size=13)
    pdf.set_xy(_MARGIN, pdf.get_y())
    pdf.cell(_CW, 7, "Step-by-Step Solutions", align="L", ln=True)
    pdf.set_line_width(0.4)
    rule_y = pdf.get_y()
    pdf.line(_MARGIN, rule_y, _MARGIN + _CW, rule_y)
    pdf.set_line_width(0.2)
    pdf.ln(5)

    for i, p in enumerate(problems, 1):
        if not p.step_solution:
            continue

        # Problem number header
        pdf.set_font("Times", style="B", size=10)
        pdf.set_xy(_MARGIN, pdf.get_y())
        pdf.cell(_CW, 5.5, f"Problem {i}", ln=True)

        _draw_step_solution(pdf, p.step_solution)

        # Thin separator between problems
        sep_y = pdf.get_y()
        pdf.set_draw_color(210, 210, 210)
        pdf.line(_MARGIN, sep_y, _MARGIN + _CW, sep_y)
        pdf.set_draw_color(0, 0, 0)
        pdf.ln(4)


# ─── Document assembly ────────────────────────────────────────────────────────

def _make_pdf(r: ExportPDFRequest) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "Install required packages: pip install fpdf2 matplotlib"
        ) from exc

    class _PDF(FPDF):
        def footer(self) -> None:
            self.set_y(-12)
            self.set_font("Helvetica", size=7)
            self.set_text_color(180, 180, 180)
            self.cell(0, 5, "Generated by ExamTarget · examtarget.com", align="C")
            self.set_text_color(0, 0, 0)

    pdf = _PDF(unit="mm", format="letter")
    pdf.set_auto_page_break(auto=True, margin=_MARGIN)
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)

    # Problems page — inline steps replace work space; separate-page keeps it
    inline = r.include_steps and r.steps_placement == "inline"
    pdf.add_page()
    _draw_header(pdf, r.title, r.teacher_name, r.class_period, r.date)
    _draw_problems(pdf, r.problems, include_steps_inline=inline)

    if r.include_answer_key:
        pdf.add_page()
        _draw_header(pdf, f"{r.title} - Answer Key", "", "", "")
        _draw_answers(pdf, r.problems)

    if r.include_steps and r.steps_placement == "separate_page":
        _draw_solutions_page(pdf, r.problems)

    return bytes(pdf.output())


# ─── Route ────────────────────────────────────────────────────────────────────

@router.post("/export/pdf")
def export_pdf(body: ExportPDFRequest) -> Response:
    try:
        pdf_bytes = _make_pdf(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    safe = "".join(
        c for c in body.title if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    filename = f"{safe or 'worksheet'}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from .base import ProblemResult, TopicTemplate
from .exponents_and_radicals import ExponentsAndRadicals
from .factoring_quadratics import FactoringQuadratics
from .linear_equations import LinearEquations
from .simplifying_expressions import SimplifyingExpressions
from .systems_of_equations import SystemsOfEquations

TOPIC_REGISTRY: dict[str, type[TopicTemplate]] = {
    "linear_equations": LinearEquations,
    "systems_of_equations": SystemsOfEquations,
    "simplifying_expressions": SimplifyingExpressions,
    "exponents_and_radicals": ExponentsAndRadicals,
    "factoring_quadratics": FactoringQuadratics,
}

# Display metadata kept here so routers don't import individual topic modules.
TOPIC_METADATA: dict[str, dict[str, object]] = {
    "linear_equations": {
        "display_name": "Linear Equations",
        "standard_codes": ["CCSS.MATH.CONTENT.HSA-REI.B.3"],
    },
    "systems_of_equations": {
        "display_name": "Systems of Equations",
        "standard_codes": ["CCSS.MATH.CONTENT.HSA-REI.C.6"],
    },
    "simplifying_expressions": {
        "display_name": "Simplifying Expressions",
        "standard_codes": ["CCSS.MATH.CONTENT.HSA-SSE.A.1"],
    },
    "exponents_and_radicals": {
        "display_name": "Exponents & Radicals",
        "standard_codes": ["CCSS.MATH.CONTENT.HSA-SSE.B.3"],
    },
    "factoring_quadratics": {
        "display_name": "Factoring Quadratics",
        "standard_codes": [
            "CCSS.MATH.CONTENT.HSA-SSE.B.3",
            "CCSS.MATH.CONTENT.HSA-APR.B.3",
        ],
    },
}

__all__ = ["TOPIC_REGISTRY", "TOPIC_METADATA", "TopicTemplate", "ProblemResult"]

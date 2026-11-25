"""ULTRON original mathematical reasoning core prototype."""
from .config import NeuroSparseConfig, count_parameters
from .model import NeuroSparseModel
from .math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from .math_tokenizer import MathTokenizer, MathVocabulary
from .data_generation import MathExample, generate_examples
from .math_parser import MathParser, MathParseError, parse_math
from .symbolic import simplify
from .polynomial import Polynomial, PolynomialError, PolynomialLimits
from .rational import RationalFunction, RationalExpressionError, RationalDomainError
from .algebraic import RealAlgebraicNumber
from .algebraic_arithmetic import resultant_polynomial

__all__ = ["NeuroSparseConfig", "count_parameters", "NeuroSparseModel", "Expr", "ExprKind", "FormulaCandidate", "VerificationStatus", "MathTokenizer", "MathVocabulary", "MathExample", "generate_examples", "MathParser", "MathParseError", "parse_math", "simplify", "Polynomial", "PolynomialError", "PolynomialLimits", "RationalFunction", "RationalExpressionError", "RationalDomainError", "RealAlgebraicNumber", "resultant_polynomial"]

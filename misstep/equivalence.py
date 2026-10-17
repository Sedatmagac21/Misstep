"""Mathematical equivalence checks between two lines of work."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

import sympy as sp

from .parsing import Line


class Match(str, Enum):
    EXACT = "exact"          # same expression / both sides individually equal
    PROPORTIONAL = "proportional"  # equations differ by a nonzero constant factor
    SAME_SOLUTIONS = "same_solutions"  # only the solution sets agree
    NONE = "none"


def value(expr: sp.Expr) -> sp.Expr:
    """Evaluate an unevaluated tree to its canonical value."""
    return _value(sp.sstr(expr))


@lru_cache(maxsize=4096)
def _value(text: str) -> sp.Expr:
    return sp.simplify(sp.sympify(text))


def is_zero(expr: sp.Expr) -> bool:
    diff = sp.simplify(sp.expand(expr))
    if diff == 0:
        return True
    return bool(diff.equals(0)) if diff.free_symbols else False


def unknown(*lines: Line) -> sp.Symbol | None:
    symbols: set[sp.Symbol] = set()
    for line in lines:
        symbols |= value(line.lhs).free_symbols
        if line.rhs is not None:
            symbols |= value(line.rhs).free_symbols
    if not symbols:
        return None
    return sorted(symbols, key=lambda s: (s.name != "x", s.name))[0]


def solutions(line: Line, var: sp.Symbol) -> sp.Set:
    assert line.rhs is not None
    return sp.solveset(sp.Eq(value(line.lhs), value(line.rhs)), var, domain=sp.S.Reals)


def compare(a: Line, b: Line) -> Match:
    """How strongly does line ``b`` agree with line ``a``?"""
    if a.is_equation != b.is_equation:
        return Match.NONE
    if not a.is_equation:
        return Match.EXACT if is_zero(value(a.lhs) - value(b.lhs)) else Match.NONE

    al, ar, bl, br = (value(e) for e in (a.lhs, a.rhs, b.lhs, b.rhs))
    if (is_zero(al - bl) and is_zero(ar - br)) or (is_zero(al - br) and is_zero(ar - bl)):
        return Match.EXACT
    da, db = sp.simplify(al - ar), sp.simplify(bl - br)
    if db != 0:
        ratio = sp.simplify(da / db)
        if ratio.is_number and ratio != 0:
            return Match.PROPORTIONAL
    var = unknown(a, b)
    if var is not None and solutions(a, var) == solutions(b, var):
        return Match.SAME_SOLUTIONS
    return Match.NONE


def equivalent(a: Line, b: Line) -> bool:
    return compare(a, b) is not Match.NONE

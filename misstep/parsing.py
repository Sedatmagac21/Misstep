"""Parse a handwritten-style math line into an *unevaluated* SymPy tree.

SymPy normally simplifies while parsing (``3x-(x+3)`` becomes ``2x-3``), which
would erase the very structure a student's mistake lives in. We therefore build
the tree ourselves from Python's AST with ``evaluate=False`` everywhere.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

import sympy as sp


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Line:
    """One line of student work: an equation (lhs = rhs) or a bare expression."""

    raw: str
    lhs: sp.Expr
    rhs: sp.Expr | None = None

    @property
    def is_equation(self) -> bool:
        return self.rhs is not None

    def pretty(self) -> str:
        if self.is_equation:
            return f"{sp.sstr(self.lhs)} = {sp.sstr(self.rhs)}"
        return sp.sstr(self.lhs)


_REPLACEMENTS = {
    "−": "-", "–": "-", "—": "-", "×": "*", "·": "*", "⋅": "*", "÷": "/",
    ":": "/",  # Turkish schools write division as ':'
    "²": "^2", "³": "^3", "√": "sqrt", ",": ".",
}

_TOKEN = re.compile(r"\s*(sqrt|\d+(?:\.\d+)?|[A-Za-z]|\*\*|[-+*/^()])")


def _tokenize(text: str) -> list[str]:
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ParseError(f"Okunamayan karakter: {text[pos:]!r}")
        tokens.append(m.group(1))
        pos = m.end()
    return tokens


def _insert_implicit_mult(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        if out:
            prev = out[-1]
            prev_ends_value = prev == ")" or prev[0].isdigit() or (prev.isalpha() and prev != "sqrt")
            tok_starts_value = tok == "(" or tok.isalpha() or (tok[0].isdigit() and prev.isalpha() and prev != "sqrt")
            if prev_ends_value and tok_starts_value:
                out.append("*")
        out.append(tok)
    return ["**" if t == "^" else t for t in out]


def _num(text: str) -> sp.Rational:
    return sp.Rational(text)


def _build(node: ast.AST) -> sp.Expr:
    if isinstance(node, ast.Expression):
        return _build(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return _num(repr(node.value)) if isinstance(node.value, float) else sp.Integer(node.value)
    if isinstance(node, ast.Name):
        return sp.Symbol(node.id)
    if isinstance(node, ast.UnaryOp):
        operand = _build(node.operand)
        if isinstance(node.op, ast.USub):
            if operand.is_Number:
                return -operand
            return sp.Mul(sp.Integer(-1), operand, evaluate=False)
        if isinstance(node.op, ast.UAdd):
            return operand
    if isinstance(node, ast.BinOp):
        a, b = _build(node.left), _build(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return sp.Add(a, b, evaluate=False)
        if isinstance(op, ast.Sub):
            neg_b = -b if b.is_Number else sp.Mul(sp.Integer(-1), b, evaluate=False)
            return sp.Add(a, neg_b, evaluate=False)
        if isinstance(op, ast.Mult):
            return sp.Mul(a, b, evaluate=False)
        if isinstance(op, ast.Div):
            return sp.Mul(a, sp.Pow(b, sp.Integer(-1), evaluate=False), evaluate=False)
        if isinstance(op, ast.Pow):
            return sp.Pow(a, b, evaluate=False)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1:
        return sp.Pow(_build(node.args[0]), sp.Rational(1, 2), evaluate=False)
    raise ParseError(f"Desteklenmeyen ifade: {ast.dump(node)[:60]}")


def parse_expression(text: str) -> sp.Expr:
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    if not text.strip():
        raise ParseError("Boş ifade")
    code = " ".join(_insert_implicit_mult(_tokenize(text)))
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError as exc:
        raise ParseError(f"Sözdizimi hatası: {text!r}") from exc
    return _build(tree)


def parse_line(text: str) -> Line:
    parts = text.split("=")
    if len(parts) == 1:
        return Line(raw=text, lhs=parse_expression(parts[0]))
    if len(parts) == 2:
        return Line(raw=text, lhs=parse_expression(parts[0]), rhs=parse_expression(parts[1]))
    raise ParseError(f"Birden fazla '=' var: {text!r}")

"""Library of known algebra "bug rules".

Each rule is a *wrong* transformation that real students apply (after Brown &
Burton's BUGGY, 1978). To diagnose a wrong step we apply every rule to the
previous line and look for the rule that reproduces what the student wrote.
The diagnosis is therefore a reconstruction, not a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator

import sympy as sp

from .parsing import Line


@dataclass(frozen=True)
class BugRule:
    id: str
    name: str
    misconception: str
    correct_rule: str
    example: str
    apply: Callable[[Line], Iterator[Line]] = field(repr=False, compare=False)


def _ue_add(*args: sp.Expr) -> sp.Expr:
    return sp.Add(*args, evaluate=False) if len(args) > 1 else args[0]


def _ue_mul(*args: sp.Expr) -> sp.Expr:
    return sp.Mul(*args, evaluate=False)


def _subtrees(expr: sp.Expr) -> Iterator[sp.Expr]:
    yield expr
    for arg in expr.args:
        yield from _subtrees(arg)


def _on_subtrees(rewrite: Callable[[sp.Expr], Iterator[sp.Expr]]) -> Callable[[Line], Iterator[Line]]:
    """Lift a sub-expression rewrite to every place it can apply in a line."""

    def apply(line: Line) -> Iterator[Line]:
        sides = [("lhs", line.lhs)] + ([("rhs", line.rhs)] if line.is_equation else [])
        for side_name, side in sides:
            for sub in _subtrees(side):
                for new in rewrite(sub):
                    replaced = side.xreplace({sub: new})
                    if side_name == "lhs":
                        yield Line(raw="", lhs=replaced, rhs=line.rhs)
                    else:
                        yield Line(raw="", lhs=line.lhs, rhs=replaced)

    return apply


def _split_coeff(expr: sp.Expr) -> tuple[sp.Expr, sp.Expr]:
    """Split a product into (numeric coefficient, rest) without evaluating rest."""
    if isinstance(expr, sp.Mul):
        nums = [a for a in expr.args if a.is_Number]
        rest = [a for a in expr.args if not a.is_Number]
        coeff = sp.Mul(*nums) if nums else sp.Integer(1)
        inner_c, inner_rest = (_split_coeff(rest[0]) if len(rest) == 1 else (sp.Integer(1), _ue_mul(*rest) if rest else sp.Integer(1)))
        return coeff * inner_c, inner_rest
    return sp.Integer(1), expr


def _add_terms(expr: sp.Expr) -> list[sp.Expr]:
    out = []
    for a in (expr.args if isinstance(expr, sp.Add) else (expr,)):
        out.extend(_add_terms(a) if isinstance(a, sp.Add) else [a])
    return out


# --- expression-level rewrites -------------------------------------------------

def _distribute_sign_first_only(sub):
    c, rest = _split_coeff(sub)
    if c < 0 and isinstance(rest, sp.Add):
        terms = _add_terms(rest)
        yield _ue_add(c * terms[0], *[(-c) * t for t in terms[1:]])


def _distribute_first_only(sub):
    c, rest = _split_coeff(sub)
    if c not in (1, -1) and isinstance(rest, sp.Add):
        terms = _add_terms(rest)
        yield _ue_add(c * terms[0], *terms[1:])


def _square_of_sum(sub):
    if isinstance(sub, sp.Pow) and sub.exp == 2 and isinstance(sub.base, sp.Add):
        terms = _add_terms(sub.base)
        yield _ue_add(*[t**2 for t in terms])
        if len(terms) == 2:
            a, b = terms
            sign = -1 if sp.sympify(sp.sstr(b)).could_extract_minus_sign() else 1
            yield _ue_add(a**2, sign * b**2)


def _power_rules(sub):
    if isinstance(sub, sp.Mul):
        pows = [a for a in sub.args if isinstance(a, sp.Pow) and a.exp.is_Number and a.exp > 0]
        syms = [a for a in sub.args if isinstance(a, sp.Symbol)]
        bases = [(p.base, p.exp) for p in pows] + [(s, sp.Integer(1)) for s in syms]
        for i in range(len(bases)):
            for j in range(i + 1, len(bases)):
                if bases[i][0] == bases[j][0]:
                    others = [a for a in sub.args if a not in (pows + syms)]
                    yield _ue_mul(*others, bases[i][0] ** (bases[i][1] * bases[j][1])) if others else bases[i][0] ** (bases[i][1] * bases[j][1])
    if isinstance(sub, sp.Pow) and isinstance(sub.base, sp.Pow):
        yield sub.base.base ** (sub.base.exp + sub.exp)


def _like_terms_multiply_power(sub):
    if isinstance(sub, sp.Add):
        terms = _add_terms(sub)
        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                ci, ri = _split_coeff(terms[i])
                cj, rj = _split_coeff(terms[j])
                if isinstance(ri, sp.Symbol) and ri == rj:
                    rest = [t for k, t in enumerate(terms) if k not in (i, j)]
                    yield _ue_add((ci + cj) * ri**2, *rest)


def _combine_unlike(sub):
    if isinstance(sub, sp.Add):
        terms = _add_terms(sub)
        for i, ti in enumerate(terms):
            ci, ri = _split_coeff(ti)
            if not ri.free_symbols:
                continue
            for j, tj in enumerate(terms):
                if tj.is_Number and i != j:
                    rest = [t for k, t in enumerate(terms) if k not in (i, j)]
                    yield _ue_add((ci + tj) * ri, *rest)


def _fraction_rules(sub):
    num, den = sp.fraction(sub)
    if den == 1 or not isinstance(num, sp.Add):
        return
    terms = _add_terms(num)
    for k, t in enumerate(terms):  # (a + b)/b -> a   (illegal cancellation)
        if sp.simplify(sp.sympify(sp.sstr(t)) - sp.sympify(sp.sstr(den))) == 0:
            rest = terms[:k] + terms[k + 1:]
            yield _ue_add(*rest)
    yield _ue_add(_ue_mul(terms[0], sp.Pow(den, -1, evaluate=False)), *terms[1:])  # divide first term only


def _add_fractions(sub):
    if isinstance(sub, sp.Add):
        fracs = [sp.fraction(t) for t in _add_terms(sub)]
        if len(fracs) == 2 and all(d != 1 for _, d in fracs):
            (a, b), (c, d) = fracs
            yield _ue_mul(_ue_add(a, c), sp.Pow(_ue_add(b, d), -1, evaluate=False))


def _sqrt_of_sum(sub):
    if isinstance(sub, sp.Pow) and sub.exp == sp.Rational(1, 2) and isinstance(sub.base, sp.Add):
        yield _ue_add(*[sp.sqrt(t) for t in _add_terms(sub.base)])


# --- equation-level rewrites ---------------------------------------------------

def _move_without_sign_change(line: Line):
    if not line.is_equation:
        return
    for src, dst, from_left in ((line.lhs, line.rhs, True), (line.rhs, line.lhs, False)):
        terms = _add_terms(src)
        if len(terms) < 2:
            continue
        for k, t in enumerate(terms):
            remaining = _ue_add(*(terms[:k] + terms[k + 1:]))
            moved = _ue_add(dst, t)
            yield Line("", remaining, moved) if from_left else Line("", moved, remaining)


def _wrong_inverse_operation(line: Line):
    if not line.is_equation:
        return
    for side, other, left in ((line.lhs, line.rhs, True), (line.rhs, line.lhs, False)):
        c, rest = _split_coeff(side)
        if isinstance(rest, sp.Symbol) and c not in (0, 1):
            for wrong in (_ue_add(other, -c), _ue_mul(other, c), _ue_mul(c, sp.Pow(other, -1, evaluate=False))):
                yield Line("", rest, wrong) if left else Line("", wrong, rest)


def _divide_or_multiply_partially(line: Line):
    if not line.is_equation:
        return
    numbers = {abs(a) for a in sp.preorder_traversal(line.lhs) if a.is_Integer and abs(a) > 1}
    numbers |= {abs(a) for a in sp.preorder_traversal(line.rhs) if a.is_Integer and abs(a) > 1}
    for k in numbers:
        for side, other, left in ((line.lhs, line.rhs, True), (line.rhs, line.lhs, False)):
            terms = _add_terms(side)
            var_terms = [t for t in terms if t.free_symbols]
            const_terms = [t for t in terms if not t.free_symbols]
            if var_terms and const_terms:
                divided = _ue_add(*[t / k for t in var_terms], *const_terms)
                yield Line("", divided, other / k) if left else Line("", other / k, divided)
                multiplied = _ue_add(*[t * k for t in var_terms], *const_terms)
                yield Line("", multiplied, other * k) if left else Line("", other * k, multiplied)
            # only one side divided / multiplied
            yield Line("", side / k, other) if left else Line("", other, side / k)
            yield Line("", side * k, other) if left else Line("", other, side * k)


def _lose_negative_root(line: Line):
    if not line.is_equation:
        return
    for side, other in ((line.lhs, line.rhs), (line.rhs, line.lhs)):
        if isinstance(side, sp.Pow) and side.exp == 2 and isinstance(side.base, sp.Symbol):
            yield Line("", side.base, sp.sqrt(other))


RULES: list[BugRule] = [
    BugRule("SIGN_DISTRIBUTION", "Eksiyi parantezin sadece ilk terimine dağıtma",
            "Parantezin önündeki eksi işaretinin yalnızca ilk terimi etkilediğini düşünüyor.",
            "−(a + b) = −a − b: eksi, parantezin içindeki her terimin işaretini değiştirir.",
            "−(x + 3) → −x + 3", _on_subtrees(_distribute_sign_first_only)),
    BugRule("PARTIAL_DISTRIBUTION", "Çarpanı parantezin sadece ilk terimine dağıtma",
            "Dağılma özelliğinde katsayının yalnızca ilk terimle çarpıldığını düşünüyor.",
            "k(a + b) = ka + kb", "2(x + 3) → 2x + 3", _on_subtrees(_distribute_first_only)),
    BugRule("SQUARE_OF_SUM", "Toplamın karesini terimlerin karelerinin toplamı sanma",
            "(a + b)² ifadesinin a² + b² olduğunu düşünüyor; ortadaki 2ab terimini unutuyor.",
            "(a + b)² = a² + 2ab + b²", "(x + 3)² → x² + 9", _on_subtrees(_square_of_sum)),
    BugRule("POWER_RULES", "Üslü sayılarda çarpma/kuvvet kuralını karıştırma",
            "Aynı tabanlı çarpımda üsleri çarpıyor ya da kuvvetin kuvvetinde üsleri topluyor.",
            "xᵃ · xᵇ = xᵃ⁺ᵇ ve (xᵃ)ᵇ = xᵃᵇ", "x² · x³ → x⁶", _on_subtrees(_power_rules)),
    BugRule("LIKE_TERMS_POWER", "Benzer terimleri toplarken üssü artırma",
            "x + x toplamının x² olduğunu düşünüyor; toplama ile çarpmayı karıştırıyor.",
            "ax + bx = (a + b)x; üs değişmez.", "2x + 3x → 5x²", _on_subtrees(_like_terms_multiply_power)),
    BugRule("COMBINE_UNLIKE", "Benzer olmayan terimleri birleştirme",
            "Değişkenli terim ile sabit terimi tek terim gibi topluyor.",
            "2x + 3 daha fazla sadeleşmez.", "2x + 3 → 5x", _on_subtrees(_combine_unlike)),
    BugRule("ILLEGAL_CANCELLATION", "Kesirde terim sadeleştirme",
            "Payda ile paydaki tek bir terimi sadeleştirebileceğini ya da paydanın yalnızca ilk terimi böldüğünü düşünüyor.",
            "Sadeleştirme yalnızca çarpanlar arasında yapılır: (x + 3)/3 = x/3 + 1.",
            "(x + 3)/3 → x", _on_subtrees(_fraction_rules)),
    BugRule("ADD_FRACTIONS", "Kesirleri pay paya, payda paydaya toplama",
            "a/b + c/d toplamının (a + c)/(b + d) olduğunu düşünüyor.",
            "a/b + c/d = (ad + bc)/bd", "x/2 + x/3 → 2x/5", _on_subtrees(_add_fractions)),
    BugRule("SQRT_OF_SUM", "Toplamın karekökünü köklerin toplamı sanma",
            "√(a + b) = √a + √b olduğunu düşünüyor.", "√(a + b) genel olarak √a + √b değildir.",
            "√(x² + 9) → x + 3", _on_subtrees(_sqrt_of_sum)),
    BugRule("MOVE_WITHOUT_SIGN_CHANGE", "Terimi karşıya işaret değiştirmeden geçirme",
            "Eşitliğin diğer tarafına geçen terimin işaretinin aynı kaldığını düşünüyor.",
            "Her iki taraftan aynı sayı çıkarılır: x + 3 = 7 ⇒ x = 7 − 3.",
            "x + 3 = 7 → x = 7 + 3", _move_without_sign_change),
    BugRule("WRONG_INVERSE_OPERATION", "Katsayıyı yanlış ters işlemle karşıya geçirme",
            "Çarpım durumundaki katsayıyı karşıya çıkararak, çarparak ya da ters bölerek geçiriyor.",
            "3x = 12 ⇒ x = 12 / 3 (çarpmanın tersi bölmedir).",
            "3x = 12 → x = 12 − 3", _wrong_inverse_operation),
    BugRule("PARTIAL_BOTH_SIDES", "Bölme/çarpmayı tüm terimlere uygulamama",
            "Eşitliği bir sayıyla bölerken ya da çarparken bazı terimleri veya bir tarafı atlıyor.",
            "Eşitliğin iki tarafındaki her terim aynı sayıyla bölünür/çarpılır.",
            "2x + 4 = 10 → x + 4 = 5", _divide_or_multiply_partially),
    BugRule("LOSE_NEGATIVE_ROOT", "Karekök alırken negatif kökü unutma",
            "x² = 9 denkleminin tek çözümünün 3 olduğunu düşünüyor.",
            "x² = 9 ⇒ x = 3 veya x = −3", "x² = 9 → x = 3", _lose_negative_root),
]

RULES_BY_ID = {r.id: r for r in RULES}

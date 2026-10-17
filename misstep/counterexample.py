"""Turn a wrong step into a concrete numeric counterexample the student can check."""

from __future__ import annotations

import sympy as sp

from .equivalence import solutions, unknown, value
from .parsing import Line


def _fmt(v: sp.Expr) -> str:
    return sp.sstr(sp.nsimplify(v))


_EN = {
    "pick": "Put your answer ({var} = {v}) back into the equation: the left side is {l}, the right side is {r}. They are not equal, so this answer does not satisfy the equation.",
    "step": "Your line says {var} = {v}. Put that into the previous line: the left side is {l}, the right side is {r}. They are not equal, so the equation changed in this step.",
    "lost": "{var} = {v} satisfies the previous line but not yours. A solution was lost in this step.",
    "pick_expr": "For {var} = {v} the question gives {a}, your answer gives {b}. If they were equal they would agree for every value.",
    "step_expr": "For {var} = {v} the previous expression is {a} and yours is {b}. If they were equal they would agree for every value.",
}


def counterexample(prev: Line, cur: Line, practice: bool = False, lang: str = "tr") -> str | None:
    var = unknown(prev, cur)
    if var is None:
        return None
    if prev.is_equation and cur.is_equation:
        cur_sols, prev_sols = solutions(cur, var), solutions(prev, var)
        if isinstance(cur_sols, sp.FiniteSet):
            for v in cur_sols:
                if v not in prev_sols:
                    left, right = value(prev.lhs).subs(var, v), value(prev.rhs).subs(var, v)
                    if lang == "en":
                        return _EN["pick" if practice else "step"].format(var=var, v=_fmt(v), l=_fmt(left), r=_fmt(right))
                    if practice:
                        return (f"Seçtiğin cevabı ({var} = {_fmt(v)}) denklemde yerine koyalım: sol taraf {_fmt(left)}, "
                                f"sağ taraf {_fmt(right)}. Eşit olmadıkları için bu cevap denklemi sağlamıyor.")
                    return (f"Yazdığın satıra göre {var} = {_fmt(v)} olmalı. Ama bunu bir önceki satırda yerine koyarsak "
                            f"sol taraf {_fmt(left)}, sağ taraf {_fmt(right)} çıkıyor. Eşit değiller, yani bu adımda denklem değişmiş.")
        if isinstance(prev_sols, sp.FiniteSet):
            for v in prev_sols:
                if v not in cur_sols:
                    if lang == "en":
                        return _EN["lost"].format(var=var, v=_fmt(v))
                    return (f"{var} = {_fmt(v)} bir önceki satırı sağlıyor ama yazdığın satırı sağlamıyor. "
                            "Bu adımda bir çözüm kaybolmuş.")
        return None
    if not prev.is_equation and not cur.is_equation:
        a, b = value(prev.lhs), value(cur.lhs)
        for v in (2, 1, 3, -1, 4, 5):
            va, vb = a.subs(var, v), b.subs(var, v)
            if va.is_number and vb.is_number and sp.simplify(va - vb) != 0:
                if lang == "en":
                    return _EN["pick_expr" if practice else "step_expr"].format(var=var, v=v, a=_fmt(va), b=_fmt(vb))
                if practice:
                    return f"{var} = {v} için soru {_fmt(va)}, seçtiğin cevap {_fmt(vb)} veriyor. Eşit olsalardı her değerde aynı çıkarlardı."
                return f"{var} = {v} için önceki ifade {_fmt(va)}, yazdığın ifade {_fmt(vb)} oluyor. Eşit olsalardı her değerde aynı çıkarlardı."
    return None

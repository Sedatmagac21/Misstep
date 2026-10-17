"""English texts for the bug rules and topics (Turkish is the source language)."""

from __future__ import annotations

from .bugs import RULES_BY_ID
from .progress import TOPICS

RULES_EN: dict[str, tuple[str, str, str]] = {  # id -> (name, misconception, correct rule)
    "SIGN_DISTRIBUTION": ("Applying a minus sign only to the first term",
                          "Thinks the minus in front of brackets only changes the first term.",
                          "−(a + b) = −a − b: the minus changes the sign of every term inside."),
    "PARTIAL_DISTRIBUTION": ("Multiplying only the first term of a bracket",
                             "Thinks a factor multiplies only the first term when distributing.",
                             "k(a + b) = ka + kb"),
    "SQUARE_OF_SUM": ("Squaring a sum term by term",
                      "Thinks (a + b)² is a² + b² and forgets the middle 2ab term.",
                      "(a + b)² = a² + 2ab + b²"),
    "POWER_RULES": ("Mixing up the power rules",
                    "Multiplies exponents when multiplying powers, or adds them for a power of a power.",
                    "xᵃ · xᵇ = xᵃ⁺ᵇ and (xᵃ)ᵇ = xᵃᵇ"),
    "LIKE_TERMS_POWER": ("Raising the power when adding like terms",
                         "Thinks x + x is x²; confuses addition with multiplication.",
                         "ax + bx = (a + b)x; the exponent does not change."),
    "COMBINE_UNLIKE": ("Combining unlike terms",
                       "Adds a variable term and a constant as if they were one term.",
                       "2x + 3 cannot be simplified further."),
    "ILLEGAL_CANCELLATION": ("Cancelling terms in a fraction",
                             "Cancels a single term of the numerator with the denominator.",
                             "Only factors cancel: (x + 3)/3 = x/3 + 1."),
    "ADD_FRACTIONS": ("Adding numerators and denominators",
                      "Thinks a/b + c/d = (a + c)/(b + d).",
                      "a/b + c/d = (ad + bc)/bd"),
    "SQRT_OF_SUM": ("Taking the root of a sum term by term",
                    "Thinks √(a + b) = √a + √b.",
                    "√(a + b) is in general not √a + √b."),
    "MOVE_WITHOUT_SIGN_CHANGE": ("Moving a term without changing its sign",
                                 "Thinks a term keeps its sign when it moves to the other side.",
                                 "Subtract the same number from both sides: x + 3 = 7 ⇒ x = 7 − 3."),
    "WRONG_INVERSE_OPERATION": ("Using the wrong inverse operation",
                                "Moves a coefficient by subtracting, multiplying or dividing the wrong way.",
                                "3x = 12 ⇒ x = 12 / 3 (the inverse of multiplying is dividing)."),
    "PARTIAL_BOTH_SIDES": ("Dividing only some of the terms",
                           "Skips some terms or one side when dividing or multiplying an equation.",
                           "Every term on both sides is divided or multiplied by the same number."),
    "LOSE_NEGATIVE_ROOT": ("Forgetting the negative root",
                           "Thinks the only solution of x² = 9 is 3.",
                           "x² = 9 ⇒ x = 3 or x = −3"),
}

TOPICS_EN = {
    "Parantez ve dağılma": "Brackets and distribution",
    "Denklem çözme": "Solving equations",
    "Terimler ve sadeleştirme": "Terms and simplifying",
    "Kesirli ifadeler": "Fractions",
    "Özdeşlikler": "Identities",
    "Üslü ve köklü ifadeler": "Powers and roots",
    "İkinci dereceden denklemler": "Quadratic equations",
}

assert set(RULES_EN) == set(RULES_BY_ID) and set(TOPICS_EN) == set(TOPICS)


def rule_text(rule_id: str, lang: str = "tr") -> dict:
    rule = RULES_BY_ID.get(rule_id)
    if rule is None:
        return {"id": rule_id, "name": rule_id, "misconception": "", "correct_rule": "", "example": ""}
    if lang == "en":
        name, mis, correct = RULES_EN[rule_id]
    else:
        name, mis, correct = rule.name, rule.misconception, rule.correct_rule
    return {"id": rule_id, "name": name, "misconception": mis, "correct_rule": correct, "example": rule.example}


def topic_name(topic: str, lang: str = "tr") -> str:
    return TOPICS_EN.get(topic, topic) if lang == "en" else topic

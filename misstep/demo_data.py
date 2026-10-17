"""Demo accounts with ten weeks of realistic practice, for trying the site and for presentations.

python -m misstep.demo_data      # creates the demo class (all demo accounts use the password demo1234)

Everything created here is clearly labelled "Demo" and lives only in the local database.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .bugs import RULES
from .documents import chunk_text
from .progress import Store
from .rag import embed_passages

DEMO = "Demo Öğrenci"
DEMO_PASSWORD = "demo1234"
EMAILS = {"student": "ogrenci@demo.misstep", "teacher": "ogretmen@demo.misstep", "parent": "veli@demo.misstep"}
SIBLING, SIBLING_EMAIL = "Ali (Demo)", "ogrenci6@demo.misstep"
TEACHER_NOTE = """
# Parantez önünde eksi varsa

Parantezin önündeki eksi işareti, parantezin içindeki HER terimi etkiler. -(x + 3) ifadesi -x - 3 olur, -x + 3 olmaz.
Bunu -1 ile çarpmak gibi düşünün: -1 · x = -x ve -1 · 3 = -3.

# Sayıyla kontrol

x = 1 koyun: -(1 + 3) = -4. Yanlış açılım -1 + 3 = 2 verir, doğru açılım -1 - 3 = -4 verir. Sonuçlar farklıysa açılım yanlıştır.

# Sınıfta sık görülen hata

3x - (x - 5) ifadesinde öğrenciler -5'i değiştirmeyi unutur. Doğrusu 3x - x + 5 = 2x + 5 olur.
Ödevlerde her parantezi açtıktan sonra x = 1 ile kontrol etmenizi istiyorum.
"""
MORE_KIDS = [("Elif (Demo)", "ogrenci7@demo.misstep", 7, 0.45, 31, 25), ("Kaan (Demo)", "ogrenci8@demo.misstep", 9, 0.3, 37, 12)]
CLASSMATES = [("Ece (Demo)", 0.55, 9), ("Mert (Demo)", 0.35, 11), ("Zeynep (Demo)", 0.7, 13), ("Can (Demo)", 0.25, 17)]


def seed(store: Store, student: str = DEMO, days: int = 70, rng_seed: int = 7, base: float | None = None) -> None:
    rng = random.Random(rng_seed)
    store.clear(student)
    # each misconception starts at a different skill and improves at its own pace
    skill = {r.id: rng.uniform(0.25, 0.7) if base is None else min(0.9, max(0.1, base + rng.uniform(-0.2, 0.2))) for r in RULES}
    if base is None:
        skill["SIGN_DISTRIBUTION"], skill["ADD_FRACTIONS"] = 0.2, 0.15   # the demo student's real weak spots
    now = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
    for back in range(days, -1, -1):
        day = now - timedelta(days=back)
        if rng.random() < (0.35 if back > 30 else 0.75):  # studies more often lately
            for _ in range(rng.randint(2, 9)):
                rid = rng.choice(list(skill))
                ok = rng.random() < skill[rid]
                kind = rng.choice(["practice", "practice", "solution"])
                store.add(student, kind, rid, ok, {"demo": True}, ts=day + timedelta(minutes=rng.randint(0, 120)))
                skill[rid] = min(0.97, skill[rid] + (0.03 if ok else 0.015) * (0.3 if rid == "ADD_FRACTIONS" else 1))


def ensure_demo(accounts, store: Store) -> dict[str, str]:
    """Create the demo teacher, class, students and parent once; return the demo e-mail per role."""
    from .progress import TOPICS

    if accounts.by_email(EMAILS["student"]):
        if not accounts.by_email(SIBLING_EMAIL):  # demo made by an older version: add the newer parts
            _extras(accounts, store, accounts.by_email(EMAILS["teacher"]), accounts.by_email(EMAILS["student"]),
                    accounts.by_email(EMAILS["parent"]))
        if not accounts.by_email(MORE_KIDS[0][1]):
            _extras_v5(accounts, store, accounts.by_email(EMAILS["teacher"]), accounts.by_email(EMAILS["parent"]))
        return EMAILS
    teacher = accounts.register("Demo Öğretmen", EMAILS["teacher"], DEMO_PASSWORD, "teacher")
    klass = accounts.create_class(teacher, "8-A (Demo)")
    student = accounts.register(DEMO, EMAILS["student"], DEMO_PASSWORD, "student", grade=8)
    accounts.join_class(student, klass["code"])
    seed(store, student.key)
    for i, (name, base, rng_seed) in enumerate(CLASSMATES):
        mate = accounts.register(name, f"ogrenci{i + 2}@demo.misstep", DEMO_PASSWORD, "student", grade=8)
        accounts.join_class(mate, klass["code"])
        seed(store, mate.key, days=rng_seed * 4, rng_seed=rng_seed, base=base)
    parent = accounts.register("Demo Veli", EMAILS["parent"], DEMO_PASSWORD, "parent")
    accounts.link_child(parent, student.family_code)
    accounts.create_assignment(teacher, klass["id"], "Parantez ve kesir tekrarı",
                               TOPICS["Parantez ve dağılma"] + TOPICS["Kesirli ifadeler"], "medium", 8,
                               (datetime.now() + timedelta(days=3)).date().isoformat())
    _extras(accounts, store, teacher, student, parent)
    _extras_v5(accounts, store, teacher, parent)
    return EMAILS


def _extras(accounts, store: Store, teacher, student, parent) -> None:
    """A second child for the parent, finished tests and a teacher's lesson file."""
    sibling = accounts.register(SIBLING, SIBLING_EMAIL, DEMO_PASSWORD, "student", grade=10)
    seed(store, sibling.key, days=40, rng_seed=23, base=0.6)
    accounts.link_child(parent, sibling.family_code)
    now = datetime.now()
    for back, (n, c, w, lv) in enumerate([(10, 8, 2, "medium"), (8, 5, 3, "adaptive"), (10, 6, 3, "medium"), (5, 2, 3, "easy")]):
        accounts.save_test(student, {"total": n, "correct": c, "wrong": w, "blank": n - c - w, "seconds": 60 * n + 37 * back,
                                     "level": lv, "adaptive": lv == "adaptive", "topics": ["Parantez ve dağılma", "Kesirli ifadeler"],
                                     "weak": [RULES[0].name]}, created=now - timedelta(days=1 + back * 3))
    text = TEACHER_NOTE.strip()
    passages = chunk_text(text)
    accounts.add_document(teacher, "Parantez ve eksi işareti (ders notu)", "parantez-ders-notu.md", "md", text.encode(),
                          text, passages, embed_passages([f"Parantez ve eksi işareti\n{p}" for p in passages]))



def _extras_v5(accounts, store: Store, teacher, parent) -> None:
    """Two more children for the parent and the sample PDFs the teacher shares with the class."""
    from .documents import extract_text
    from .samples import build_samples

    now = datetime.now()
    for name, email, grade, base, rng_seed, days in MORE_KIDS:
        kid = accounts.register(name, email, DEMO_PASSWORD, "student", grade=grade)
        seed(store, kid.key, days=days, rng_seed=rng_seed, base=base)
        accounts.link_child(parent, kid.family_code)
        n, c = 10, round(10 * (base + 0.15))
        accounts.save_test(kid, {"total": n, "correct": c, "wrong": n - c - 1, "blank": 1, "seconds": 540, "level": "easy",
                                 "adaptive": False, "topics": ["Denklem çözme"], "weak": [RULES[-3].name]}, created=now - timedelta(days=2))
    # some homework progress, so the teacher's table and the weekly report show who has finished
    for cls in accounts.classes_of_teacher(teacher):
        for hw in accounts.assignments_for_class(cls["id"]):
            for k, mate in enumerate(cls["students"]):
                done = [hw["count"], hw["count"] // 2, hw["count"], 2, 0, hw["count"]][k % 6]
                for i in range(done):
                    store.add(mate.key, "practice", hw["rule_ids"][i % len(hw["rule_ids"])], (i + k) % 3 != 0,
                              {"assignment": hw["id"], "demo": True}, ts=now - timedelta(hours=30 - i))
    for title, path in build_samples():
        data = path.read_bytes()
        text = extract_text(path.name, data)
        passages = chunk_text(text)
        accounts.add_document(teacher, title, path.name, "pdf", data, text, passages,
                              embed_passages([f"{title}\n{p}" for p in passages]))


if __name__ == "__main__":
    from .accounts import Accounts

    ensure_demo(Accounts(), Store())
    print("Demo hesapları hazır (şifre: demo1234):")
    for role, email in EMAILS.items():
        print(f"  {role:8} {email}")

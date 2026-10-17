"""Accounts, classes and family links, stored in the same local SQLite file.

Three roles: a student studies, a teacher runs classes and sets homework, a
parent follows their child. A student joins a class with the teacher's class
code and shares a family code with a parent. Passwords are stored as salted
PBKDF2 hashes; nothing leaves the computer.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .db import connect
from .progress import DB_PATH

ROLES = ("student", "teacher", "parent")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


def _code(n: int = 6) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


class AccountError(ValueError):
    """A request that cannot be done, with a message key the interface translates."""


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str
    grade: int | None
    family_code: str | None
    created: str

    @property
    def key(self) -> str:
        """The name this user's work is stored under in the progress store."""
        return f"user:{self.id}"

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
                "grade": self.grade, "family_code": self.family_code if self.role == "student" else None}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, role TEXT,
    pw_hash TEXT, salt TEXT, grade INTEGER, family_code TEXT UNIQUE, created TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY, teacher_id INTEGER, name TEXT, code TEXT UNIQUE, created TEXT);
CREATE TABLE IF NOT EXISTS class_members (class_id INTEGER, student_id INTEGER, joined TEXT, PRIMARY KEY (class_id, student_id));
CREATE TABLE IF NOT EXISTS parent_links (parent_id INTEGER, student_id INTEGER, PRIMARY KEY (parent_id, student_id));
CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY, class_id INTEGER, title TEXT, rule_ids TEXT,
    level TEXT, count INTEGER, due TEXT, seed INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, owner_id INTEGER, data TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS contact (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, owner_id INTEGER, title TEXT, filename TEXT, kind TEXT,
    size INTEGER, data BLOB, text TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS doc_chunks (doc_id INTEGER, idx INTEGER, text TEXT, vec TEXT, PRIMARY KEY (doc_id, idx));
CREATE TABLE IF NOT EXISTS tests (id INTEGER PRIMARY KEY, user_id INTEGER, data TEXT, created TEXT);
"""

_USER_COLS = "id, name, email, role, grade, family_code, created"


class Accounts:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = connect(self.path)
        self.db.executescript(_SCHEMA)
        self.db.commit()

    # ---- users and sessions ----
    def register(self, name: str, email: str, password: str, role: str, grade: int | None = None) -> User:
        name, email = name.strip(), email.strip().lower()
        if role not in ROLES:
            raise AccountError("err_role")
        if len(name) < 2:
            raise AccountError("err_name")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise AccountError("err_email")
        if len(password) < 6:
            raise AccountError("err_password")
        if self.db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise AccountError("err_email_taken")
        salt = secrets.token_bytes(16)
        family = _code() if role == "student" else None
        cur = self.db.execute(
            "INSERT INTO users (name, email, role, pw_hash, salt, grade, family_code, created) VALUES (?,?,?,?,?,?,?,?)",
            (name, email, role, _hash(password, salt), salt.hex(), grade if role == "student" else None, family,
             datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return self.user(cur.lastrowid)

    def login(self, email: str, password: str) -> tuple[User, str]:
        row = self.db.execute("SELECT id, pw_hash, salt FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row or not hmac.compare_digest(row[1], _hash(password, bytes.fromhex(row[2]))):
            raise AccountError("err_login")
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO sessions VALUES (?,?,?)", (token, row[0], datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return self.user(row[0]), token

    def logout(self, token: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE token=?", (token,))
        self.db.commit()

    def by_token(self, token: str | None) -> User | None:
        if not token:
            return None
        row = self.db.execute("SELECT user_id FROM sessions WHERE token=?", (token,)).fetchone()
        return self.user(row[0]) if row else None

    def user(self, user_id: int) -> User | None:
        row = self.db.execute(f"SELECT {_USER_COLS} FROM users WHERE id=?", (user_id,)).fetchone()
        return User(*row) if row else None

    def by_email(self, email: str) -> User | None:
        row = self.db.execute(f"SELECT {_USER_COLS} FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        return User(*row) if row else None

    def update_profile(self, user: User, name: str | None = None, grade: int | None = None) -> User:
        if name and len(name.strip()) >= 2:
            self.db.execute("UPDATE users SET name=? WHERE id=?", (name.strip(), user.id))
        if grade is not None and user.role == "student":
            self.db.execute("UPDATE users SET grade=? WHERE id=?", (grade, user.id))
        self.db.commit()
        return self.user(user.id)

    def counts(self) -> dict[str, int]:
        out = {r: 0 for r in ROLES}
        for role, n in self.db.execute("SELECT role, COUNT(*) FROM users GROUP BY role"):
            out[role] = n
        return out

    # ---- classes (teacher <-> students) ----
    def create_class(self, teacher: User, name: str) -> dict:
        if teacher.role != "teacher":
            raise AccountError("err_forbidden")
        if len(name.strip()) < 1:
            raise AccountError("err_name")
        code = _code()
        cur = self.db.execute("INSERT INTO classes (teacher_id, name, code, created) VALUES (?,?,?,?)",
                              (teacher.id, name.strip(), code, datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return {"id": cur.lastrowid, "name": name.strip(), "code": code}

    def join_class(self, student: User, code: str) -> dict:
        if student.role != "student":
            raise AccountError("err_forbidden")
        row = self.db.execute("SELECT id, name FROM classes WHERE code=?", (code.strip().upper(),)).fetchone()
        if not row:
            raise AccountError("err_code")
        self.db.execute("INSERT OR IGNORE INTO class_members VALUES (?,?,?)",
                        (row[0], student.id, datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return {"id": row[0], "name": row[1]}

    def classes_of_teacher(self, teacher: User) -> list[dict]:
        rows = self.db.execute("SELECT id, name, code FROM classes WHERE teacher_id=? ORDER BY id", (teacher.id,)).fetchall()
        return [{"id": r[0], "name": r[1], "code": r[2], "students": self.class_students(r[0])} for r in rows]

    def classes_of_student(self, student: User) -> list[dict]:
        rows = self.db.execute("""SELECT c.id, c.name, u.name FROM classes c JOIN class_members m ON m.class_id=c.id
                                  JOIN users u ON u.id=c.teacher_id WHERE m.student_id=? ORDER BY c.id""", (student.id,)).fetchall()
        return [{"id": r[0], "name": r[1], "teacher": r[2]} for r in rows]

    def class_students(self, class_id: int) -> list[User]:
        rows = self.db.execute(f"""SELECT {', '.join('u.' + c.strip() for c in _USER_COLS.split(','))} FROM users u
                                   JOIN class_members m ON m.student_id=u.id WHERE m.class_id=? ORDER BY u.name""",
                               (class_id,)).fetchall()
        return [User(*r) for r in rows]

    def owns_class(self, teacher: User, class_id: int) -> bool:
        return bool(self.db.execute("SELECT 1 FROM classes WHERE id=? AND teacher_id=?", (class_id, teacher.id)).fetchone())

    # ---- family links (parent <-> student) ----
    def link_child(self, parent: User, family_code: str) -> User:
        if parent.role != "parent":
            raise AccountError("err_forbidden")
        row = self.db.execute("SELECT id FROM users WHERE family_code=? AND role='student'",
                              (family_code.strip().upper(),)).fetchone()
        if not row:
            raise AccountError("err_code")
        self.db.execute("INSERT OR IGNORE INTO parent_links VALUES (?,?)", (parent.id, row[0]))
        self.db.commit()
        return self.user(row[0])

    def children(self, parent: User) -> list[User]:
        rows = self.db.execute("SELECT student_id FROM parent_links WHERE parent_id=? ORDER BY student_id", (parent.id,)).fetchall()
        return [self.user(r[0]) for r in rows]

    def can_view(self, viewer: User, student_id: int) -> bool:
        """A student sees themself, a teacher sees their class members, a parent sees linked children."""
        if viewer.role == "student":
            return viewer.id == student_id
        if viewer.role == "parent":
            return bool(self.db.execute("SELECT 1 FROM parent_links WHERE parent_id=? AND student_id=?",
                                        (viewer.id, student_id)).fetchone())
        return bool(self.db.execute("""SELECT 1 FROM class_members m JOIN classes c ON c.id=m.class_id
                                       WHERE c.teacher_id=? AND m.student_id=?""", (viewer.id, student_id)).fetchone())

    # ---- homework ----
    def create_assignment(self, teacher: User, class_id: int, title: str, rule_ids: list[str], level: str,
                          count: int, due: str | None) -> dict:
        if not self.owns_class(teacher, class_id):
            raise AccountError("err_forbidden")
        seed = secrets.randbelow(10**6)
        cur = self.db.execute(
            "INSERT INTO assignments (class_id, title, rule_ids, level, count, due, seed, created) VALUES (?,?,?,?,?,?,?,?)",
            (class_id, title.strip() or "Ödev", json.dumps(rule_ids), level, count, due or "", seed,
             datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return self.assignment(cur.lastrowid)

    def assignment(self, assignment_id: int) -> dict | None:
        row = self.db.execute("""SELECT a.id, a.class_id, a.title, a.rule_ids, a.level, a.count, a.due, a.seed, a.created, c.name
                                 FROM assignments a JOIN classes c ON c.id=a.class_id WHERE a.id=?""", (assignment_id,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "class_id": row[1], "title": row[2], "rule_ids": json.loads(row[3]), "level": row[4],
                "count": row[5], "due": row[6], "seed": row[7], "created": row[8], "class_name": row[9]}

    def assignments_for_class(self, class_id: int) -> list[dict]:
        ids = [r[0] for r in self.db.execute("SELECT id FROM assignments WHERE class_id=? ORDER BY id DESC", (class_id,))]
        return [self.assignment(i) for i in ids]

    def assignments_for_student(self, student: User) -> list[dict]:
        out = []
        for c in self.classes_of_student(student):
            out += self.assignments_for_class(c["id"])
        return out

    def can_do_assignment(self, student: User, assignment_id: int) -> bool:
        return bool(self.db.execute("""SELECT 1 FROM assignments a JOIN class_members m ON m.class_id=a.class_id
                                       WHERE a.id=? AND m.student_id=?""", (assignment_id, student.id)).fetchone())

    # ---- generated questions (the answer key stays on the server) ----
    def save_question(self, owner: User, data: dict) -> str:
        qid = secrets.token_urlsafe(9)
        self.db.execute("INSERT INTO questions VALUES (?,?,?,?)",
                        (qid, owner.id, json.dumps(data, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return qid

    def question(self, owner: User, qid: str) -> dict | None:
        row = self.db.execute("SELECT data FROM questions WHERE id=? AND owner_id=?", (qid, owner.id)).fetchone()
        return json.loads(row[0]) if row else None

    def update_question(self, owner: User, qid: str, data: dict) -> None:
        self.db.execute("UPDATE questions SET data=? WHERE id=? AND owner_id=?", (json.dumps(data, ensure_ascii=False), qid, owner.id))
        self.db.commit()

    # ---- uploaded study files ----
    def add_document(self, owner: User, title: str, filename: str, kind: str, data: bytes, text: str,
                     chunks: list[str], vectors: list | None) -> dict:
        if owner.role not in ("student", "teacher"):
            raise AccountError("err_forbidden")
        cur = self.db.execute(
            "INSERT INTO documents (owner_id, title, filename, kind, size, data, text, created) VALUES (?,?,?,?,?,?,?,?)",
            (owner.id, title.strip()[:120] or filename, filename[:200], kind, len(data), data, text,
             datetime.now().isoformat(timespec="seconds")))
        doc_id = cur.lastrowid
        self.db.executemany("INSERT INTO doc_chunks VALUES (?,?,?,?)",
                            [(doc_id, i, c, json.dumps(vectors[i]) if vectors else None) for i, c in enumerate(chunks)])
        self.db.commit()
        return self.document(owner, doc_id)

    def _doc_owners(self, viewer: User) -> list[int]:
        """Whose files a user may read: their own, plus their teachers' files for a student."""
        owners = [viewer.id]
        if viewer.role == "student":
            owners += [r[0] for r in self.db.execute(
                """SELECT DISTINCT c.teacher_id FROM classes c JOIN class_members m ON m.class_id=c.id
                   WHERE m.student_id=?""", (viewer.id,))]
        return owners

    def documents(self, viewer: User) -> list[dict]:
        owners = self._doc_owners(viewer)
        rows = self.db.execute(
            f"""SELECT d.id, d.owner_id, d.title, d.filename, d.kind, d.size, d.created, u.name,
                       (SELECT COUNT(*) FROM doc_chunks k WHERE k.doc_id=d.id)
                FROM documents d JOIN users u ON u.id=d.owner_id
                WHERE d.owner_id IN ({','.join('?' * len(owners))}) ORDER BY d.id DESC""", owners).fetchall()
        return [{"id": r[0], "mine": r[1] == viewer.id, "title": r[2], "filename": r[3], "kind": r[4], "size": r[5],
                 "created": r[6], "owner": r[7], "passages": r[8]} for r in rows]

    def document(self, viewer: User, doc_id: int, with_data: bool = False) -> dict | None:
        row = self.db.execute("SELECT owner_id, data, text FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row or row[0] not in self._doc_owners(viewer):
            return None
        meta = next(d for d in self.documents(viewer) if d["id"] == doc_id)
        meta["text"] = row[2]
        if with_data:
            meta["data"] = row[1]
        return meta

    def delete_document(self, owner: User, doc_id: int) -> None:
        if not self.db.execute("SELECT 1 FROM documents WHERE id=? AND owner_id=?", (doc_id, owner.id)).fetchone():
            raise AccountError("err_forbidden")
        self.db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        self.db.execute("DELETE FROM doc_chunks WHERE doc_id=?", (doc_id,))
        self.db.commit()

    def document_chunks(self, viewer: User) -> list[tuple[int, int, str, str, list | None, bool]]:
        """(doc_id, idx, title, text, vector, mine) for every passage the viewer may search."""
        owners = self._doc_owners(viewer)
        rows = self.db.execute(
            f"""SELECT k.doc_id, k.idx, d.title, k.text, k.vec, d.owner_id FROM doc_chunks k JOIN documents d ON d.id=k.doc_id
                WHERE d.owner_id IN ({','.join('?' * len(owners))})""", owners).fetchall()
        return [(r[0], r[1], r[2], r[3], json.loads(r[4]) if r[4] else None, r[5] == viewer.id) for r in rows]

    # ---- finished tests ----
    def save_test(self, user: User, data: dict, created: datetime | None = None) -> int:
        cur = self.db.execute("INSERT INTO tests (user_id, data, created) VALUES (?,?,?)",
                              (user.id, json.dumps(data, ensure_ascii=False), (created or datetime.now()).isoformat(timespec="seconds")))
        self.db.commit()
        return cur.lastrowid

    def tests(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = self.db.execute("SELECT id, data, created FROM tests WHERE user_id=? ORDER BY id DESC LIMIT ?",
                               (user_id, limit)).fetchall()
        return [{"id": r[0], **json.loads(r[1]), "created": r[2]} for r in rows]

    # ---- contact form ----
    def contact(self, name: str, email: str, message: str) -> None:
        if len(message.strip()) < 5 or "@" not in email:
            raise AccountError("err_contact")
        self.db.execute("INSERT INTO contact (name, email, message, created) VALUES (?,?,?,?)",
                        (name.strip()[:100], email.strip()[:200], message.strip()[:4000], datetime.now().isoformat(timespec="seconds")))
        self.db.commit()

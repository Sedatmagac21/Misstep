<p align="center"><img src="assets/wordmark.png" alt="Misstep" width="560"></p>

<p align="center"><b>The study companion that finds <i>why</i> a student got it wrong.</b><br>
Local, open source, built around Gemma 4. Algebra, grades 7–10.</p>

<p align="center">
<img alt="Gemma 4" src="https://img.shields.io/badge/model-Gemma%204%20E4B-FF5A5F">
<img alt="Runs locally" src="https://img.shields.io/badge/runs-100%25%20local-14213D">
<img alt="Tests" src="https://img.shields.io/badge/tests-108%20passing-1E9E5A">
<img alt="License" src="https://img.shields.io/badge/license-MIT-3B6FE0">
</p>

Answer apps tell a student the right answer. Misstep reads the student's **own** handwritten solution and finds the first step where it went wrong, then names the misconception behind it. From there it becomes the student's study partner:
- It explains the mistake from the student's notes.
- It builds practice that targets that exact misconception.
- It tracks every topic over weeks.
- It keeps the teacher and the parents in the loop.

Everything runs on the student's own computer, so a child's work never leaves the house.

Built in one night at MLH Hacktoberfest Hack Day Elazığ (theme: *Side Hustle*).

![Landing page](assets/screenshot-landing.png)

## What Misstep does

### For students: a full study companion
- **Check my solution.** Photograph a handwritten solution or type it.
  - Gemma 4 transcribes it line by line without correcting anything, and the student can edit the lines.
  - SymPy then checks every step.
  - The first wrong step is shown on a timeline with three things: the misconception's name, a numeric counter-example ("try x = 1: 16 ≠ 10") and an explanation that cites the notes.
- **Practice that targets the mistake.**
  - Tests at easy, medium, hard or adaptive level (harder after a right answer, easier after a wrong one), from 1 to 20 questions.
  - Gemma understands free-text requests ("5 questions on brackets with a minus sign, with a story").
  - Every answer is checked by SymPy, and the wrong options are the answers that real misconceptions produce.
  - After the test there is an evaluation: a donut of right, wrong and blank, net score, strengths, misconceptions revealed, and a "why?" for every question.
- **Study: lessons, chat and deep research.**
  - The study assistant answers only from the topic notes and the student's uploaded PDF or Word files, and cites each source.
  - Deep research splits a question into sub-questions, searches each one separately, writes a cited answer for each, sums them up, and exports a PDF with verified practice questions.
- **Mistake Hunt.** The bug rules run in reverse to plant one misconception in a correct solution. The student finds the wrong line and names the misconception, for points and streaks. Learning from erroneous examples is backed by research (Adams et al. 2014; Große & Renkl 2007).
- **Progress.**
  - A GitHub-style study calendar, a daily activity chart and mastery per topic.
  - Focus areas, a mistake notebook that turns past mistakes into a new test, and topic report PDFs.

### For teachers
- A class overview with a student × topic mastery map and the misconceptions the class shares.
- **A student table that sorts by any column**: questions, right, wrong, accuracy, this week, streak, homework, last active, weakest misconception.
- A **weekly class report PDF**.
- Homework with per-student progress.
- A worksheet generator with an answer-key PDF.
- Lesson files shared with the class.

### For parents
- Several children side by side.
- For each child: a weekly summary, homework progress, finished tests, the study calendar and the weak topics.

| | |
| --- | --- |
| ![Dashboard](assets/screenshot-dashboard.png) | ![Check a solution](assets/screenshot-check.png) |
| ![Generate a test](assets/screenshot-practice.png) | ![Evaluation](assets/screenshot-evaluation.png) |
| ![Study chat](assets/screenshot-chat.png) | ![Deep research](assets/screenshot-research.png) |
| ![Mistake hunt](assets/screenshot-hunt.png) | ![Class table](assets/screenshot-class.png) |
| ![Parent](assets/screenshot-parent.png) | ![Teacher](assets/screenshot-teacher.png) |
| ![Resources](assets/screenshot-resources.png) | ![Sign in](assets/screenshot-login.png) |

## How it works
```
photo ──► Gemma 4 (Ollama) ──► lines ──► SymPy: is each step equivalent to the last?
                                                   │ first non-equivalent step
                                                   ▼
                              13 bug rules: which misconception rewrites line k into line k+1 exactly?
                                                   │
                     ┌─────────────────────────────┼──────────────────────────────┐
                     ▼                             ▼                              ▼
        hybrid RAG (BM25 + EmbeddingGemma)   verified practice and         Bayesian Knowledge Tracing
        Gemma explains with citations        Mistake Hunt (SymPy-checked)  → mastery, calendar, reports
```
- **Gemma 4 reads and explains; it never grades.** Equivalence and every generated answer are proven symbolically by SymPy.
- **The diagnosis is a reconstruction, not a guess.** A bug rule (after Brown & Burton's BUGGY) must reproduce the student's wrong line exactly.
- **When Gemma is offline everything else still works.** The assistant says what is wrong and how to fix it, and answers with sentences taken from the sources.

## Measured, not claimed
A hand-written evaluation set: 43 solutions covering all 13 misconceptions. Run it with `python -m misstep.evaluate`.

| Metric | Result |
| --- | --- |
| First wrong step found | 100 % |
| Misconception named (top 1) | 97 % |
| False alarms on correct solutions | 0 % |
| Arithmetic slips left unlabelled (no invented misconception) | 67 % |

Every failing case is listed in the output and on the About page.

## Business model: free for students, a side income for tutors
![Pricing](assets/screenshot-pricing.png)

The student app is open source and free forever. Revenue comes from the people who use Misstep with paying students. The prices below are planned launch prices; the hackathon build is free.

| Plan | Price | For |
| --- | --- | --- |
| Student | ₺0 | Unlimited checks, study chat, deep research, practice, Mistake Hunt |
| Tutor | ₺249 / month | Private tutors: a class of up to 40, weekly class PDF, automatic parent reports |
| School | ₺15 / student / month | Many classes, install on the school's server, school-wide misconception map |

The landing page includes a **side-income calculator**. For example, a tutor who charges 30 students ₺300 a month for weekly mistake tracking earns ₺9,000 against a ₺249 plan. The pitch and the 3-minute demo script are in [PITCH.md](PITCH.md).

## Quick start
```bash
git clone https://github.com/Sedatmagac21/Misstep.git && cd Misstep
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ollama pull gemma4:e4b        # reads photos, explains, understands requests
ollama pull embeddinggemma    # semantic search for the notes (optional)
python app.py                 # opens http://localhost:7860
```
On the landing or login page, the **demo** cards sign you in as a student, a teacher or a parent. The demo creates a class:
- one teacher;
- students with ten weeks of history;
- a parent with four children;
- three sample PDFs.

Every demo account uses the password `demo1234`.

**If the assistant says Gemma is not answering**, it also shows the reason and the command to run. Usually the fix is one of these:
```bash
ollama serve                  # or open the Ollama app
ollama list                   # is gemma4:e4b there?
ollama run gemma4:e4b "merhaba"
```
Settings come from environment variables:
- `MISSTEP_MODEL`: the model (default `gemma4:e4b`).
- `OLLAMA_URL`: where Ollama runs (default `http://localhost:11434`).
- `MISSTEP_DB`: the database file (default `~/.misstep/misstep.db`).

## Tests and command line
```bash
pytest -q                                                   # 108 tests
python -m misstep "3x-(x+3)=7" "3x-x+3=7" "2x+3=7" "x=2"    # diagnose a solution in the terminal
python -m misstep.evaluate                                  # accuracy on the evaluation set (--photos for Gemma's reading)
python -m misstep.samples                                   # rebuild the sample PDFs
```

## Project layout
```
app.py                 starts the server and opens the browser
web/                   static site: vanilla JS modules, TR/EN, no build step
misstep/server.py      FastAPI JSON API + static hosting
misstep/vision.py      Gemma 4 via Ollama: photo reading, health and error diagnosis
misstep/diagnose.py    step-by-step verification + bug-rule diagnosis
misstep/bugs.py        the 13 misconception rules
misstep/generator.py   difficulty-aware verified question generator, free-text requests
misstep/practice.py    distractors = answers that misconceptions produce
misstep/hunt.py        Mistake Hunt: inject one bug rule, re-verify with diagnose.py
misstep/rag.py         hybrid retrieval over notes and uploads, cited explanations, study chat
misstep/research.py    deep research: plan → per-step retrieval and answer → summary
misstep/progress.py    attempts + Bayesian Knowledge Tracing
misstep/accounts.py    students, teachers, parents, classes, family links, homework
misstep/pdf_report.py  weekly class, worksheet, research and topic report PDFs
misstep/evaluate.py    evaluation set runner (eval/cases.jsonl)
knowledge/             topic notes used by the assistant
samples/               sample study PDFs
```
Passwords are stored as salted PBKDF2 hashes in a local SQLite file. No data is sent anywhere.

## Türkçe özet
Misstep, 7–10. sınıf cebir için yerel ve açık kaynak bir çalışma arkadaşıdır. Öğrencinin el yazısı çözümünü Gemma 4 ile okur ve SymPy ile her adımı doğrular. İlk hatalı adımı ve arkasındaki yanılgıyı bulur, notlardan kaynaklı açıklama yapar ve o yanılgıya özel doğrulanmış sorular üretir. Konu bazında ilerlemeyi takip eder. Öğretmene sınıf tablosu ve haftalık PDF, veliye çocuk raporu sunar. Öğrenciye ücretsizdir; gelir, özel ders veren öğretmenlerden ve okullardan gelir.

## License
MIT. DejaVu fonts are under their own license (`assets/fonts/README.txt`).

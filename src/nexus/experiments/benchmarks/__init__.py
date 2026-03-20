"""
benchmarks/ — Dataset loaders for Phase 1 benchmark experiments.

Each module exposes a single load() function that returns a list of
(question_id, question_text, expected_answer) tuples, ready to feed
into a runner.

  triviaqa.py  — open-domain trivia (knowledge-heavy)
  mmlu.py      — 57-subject academic knowledge (knowledge-heavy)
  synthetic.py — procedurally generated logic puzzles (zero-knowledge)
"""

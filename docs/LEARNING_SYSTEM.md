# Learning System Status

## Implemented on the open foundation branch

The interface contains one fixed arithmetic practice question (`18 × 7`). Correct answers show a short decomposition and increment a browser-local counter. This is a demonstration, not adaptive teaching or topic mastery tracking.

## Not implemented

There are no lessons, generated exercises, repeated-practice scheduler, mistake classification, difficulty progression, mastery model, or review recommendations. There is no evidence-based adaptation yet. The current counter records completion only and must not be interpreted as mastery.

## Next design requirements

Each exercise should carry a topic, difficulty, answer specification, solution steps, and verification procedure. Record attempts and mistakes separately from knowledge content. Test that recommendations change only from recorded evidence and do not infer mastery from one correct answer.

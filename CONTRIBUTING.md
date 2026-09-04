# Contributing to Swissfin Bench

Contributions are welcome. This document covers one point that is specific to contributing to a benchmark, and then the ordinary matters.

## Why one set is public and one is not

The regulatory extracts are official Swiss texts. They are public by definition and already sit in every large training corpus, and that is not a problem here. The benchmark does not test whether a model knows Swiss regulation; it tests whether the model confines itself to the document it was supplied with. A model answering from a memorised circular fails the paired test exactly as intended.

What cannot be public is the pairing of a task with its expected result. Once `expected_result` sits beside its extract in a repository that is crawled, a model can recall the label rather than reason to it. That answer key is what the unpublished set protects, and it is the only thing it protects.

Both sets are run, and the difference between them is treated as a measurement: a model scoring materially higher on the public set is exhibiting the size of its own contamination.

A task becomes public the moment it appears in a pull request, so the appropriate route depends on what the task is for:

| Purpose | Route | Destination |
|:--|:--|:--|
| Add a task, or correct or improve an existing one | Pull request | the public set |
| Propose an item for scoring | Email to contact@schmittsfn.com | the unpublished set |

Neither route is valued above the other, and both accept tasks in any language. German and Italian tasks are wanted through both: in the open, because the public set has to be broad and varied enough to be useful, and by email, because the scored set is French-only at present and public contributions alone cannot change that.

Both files carry a canary identifier. Please do not paste either of them into a hosted model.

## What a task should contain

Every task consists of one supplied document, one instruction, and one expected result. An instruction never asks the model to assess compliance, since no language model should hold that authority and the benchmark makes no such claim.

**Regulatory extracts** must be taken from a public official source and must carry its reference together with the date of the text quoted:

```yaml
source_text_references:
  - Circ.-FINMA 23/1 « Risques et résilience opérationnels – banques », Cm 70, p. 9
  - https://www.finma.ch/...
```

**All personal data must be fictional.** Please use reserved placeholders: names that are evidently invented, `example.invalid` addresses, `CH00 …` IBANs, and telephone numbers in the `+41 XX 000 00 00` range. Never use a real person, including a public figure, and never a real account, AVS or client number.

**Grounding tasks are created in pairs, and both halves are required.** The pair is the essential mechanism: the same question is asked of the same document, except that the twin omits the provision which settles it, and only that provision. The expected result changes from `SUCCESS` to `FAILURE`, where failure means that the model should state that the passage does not permit a conclusion. If the twin also alters wording, ordering or context, the pair no longer isolates what it is intended to isolate.

**Please set `checked_by`** to your name or handle once you have verified the extract against its source yourself. Tasks marked `pending independent review` have not yet been checked by a second person.

## Where help is most useful at present

- **Independent review of the existing tasks.** Every task currently reads `checked_by: pending independent review`. Verifying an extract against its official source, and confirming that a twin omits exactly one provision, is the most valuable contribution available and requires no code.
- **German and Italian tasks.** Each Swiss official language carries equal legal authority, and the task bank is at present exclusively in French. This is a genuine limitation on what the benchmark can claim.
- **The probabilistic component of grounding assessment.** Deterministic grading is preferred wherever a result can be reproduced exactly. Where a judge model is unavoidable, the protocol must address position, verbosity and self-enhancement bias, and should not rely on a single model.
- **Additional providers in the router**, and improved handling of failures for those already supported.
- **Packaging and deployment.** There is at present no Dockerfile and no deployment path.

## Ordinary matters

Please fork the repository, create a branch, and open a pull request against `main`.

```bash
python -m pip install -e ".[backoffice,test]"
python -m pytest
```

The test suite runs in a few seconds, makes no network calls and incurs no cost. Continuous integration runs it on every push and pull request. Please keep it passing, and add a test alongside any change in behaviour. The tests assert structural invariants rather than fixed counts, so they hold for whichever task file is loaded.

Please keep commits focused, and explain in the message why a change was made rather than only what it does.

An error in a regulatory extract is a correctness defect and merits an issue in its own right, whether or not a correction accompanies it.

## Security and disclosure

If you find something that should not be reported publicly, such as a credential in the history or a real identifier that has found its way into a task, please write to contact@schmittsfn.com rather than opening an issue.

## Licence

Swissfin Bench is published under the Apache License 2.0. Under section 5 of that licence, anything you deliberately submit for inclusion is contributed under the same terms unless you state otherwise. There is no separate contributor licence agreement.

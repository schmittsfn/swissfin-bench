# Contributing to Swissfin Bench

Contributions are welcome. This document covers the one thing that is unusual
about contributing to a benchmark, and then the ordinary things.

## The unusual thing: a public pull request cannot become a scoring item

The moment a task appears in a pull request it is public, and public benchmark
items end up in training corpora. A model that has seen the answer is not being
measured by it.

So there are two routes, and which one you want depends on what the task is for:

| You want to | Route | Where it ends up |
|:--|:--|:--|
| Add a demonstration task, fix or improve an existing one | Pull request | `tasks/swissfin_public_sample_v0_1.yaml` |
| Propose an item for the **scoring** set | Email `contact@schmittsfn.com` | The held-back set. Never appears in this repository |

Neither route is more valued than the other. The public sample is what lets
anyone understand and run the benchmark; it needs to be good.

Both files carry a canary GUID. Please do not paste either into a hosted model.

## What a good task looks like

Every task is one supplied document, one instruction, and one expected result.
An instruction never asks the model to appraise compliance — no LLM should have
that authority, and the benchmark makes no claim to it.

**Regulatory extracts** must come from a public official source and carry its
reference and the date of the text you quoted:

```yaml
source_text_references:
  - Circ.-FINMA 23/1 « Risques et résilience opérationnels – banques », Cm 70, p. 9
  - https://www.finma.ch/...
```

**All personal data must be fictional.** Use reserved placeholders — names that
are obviously invented, `example.invalid` addresses, `CH00 …` IBANs, phone
numbers in the `+41 XX 000 00 00` range. Never a real person, even a public
figure, and never a real account, AVS or client number.

**Grounding tasks come in pairs, and you must supply both.** The pair is the
whole idea: same question, same document, except that the twin removes the
provision that settles it — and *only* that provision. The expected result
flips from `SUCCESS` to `FAILURE`, where failure means the model should say the
passage does not permit a conclusion. If the twin also changes wording,
ordering or context, the pair no longer isolates what it claims to isolate.

**Set `checked_by`** to your name or handle once you have verified the extract
against the source yourself. Tasks marked `pending independent review` have not
been checked by a second person — see below.

## Where help is most useful right now

- **Independent review of the existing tasks.** Every task currently reads
  `checked_by: pending independent review`. Verifying an extract against its
  official source, and confirming a twin removes exactly one provision, is the
  single most valuable contribution and needs no code.
- **German and Italian tasks.** Every Swiss official language carries equal
  legal authority, and the task bank is currently French-only. This is a real
  gap in what the benchmark can claim.
- **The probabilistic half of grounding scoring.** Deterministic grading is
  preferred wherever a result can be reproduced exactly. Where a judge is
  unavoidable, the protocol has to address position, verbosity and
  self-enhancement bias, and should not rest on a single model.
- **More providers in the router**, and better failure handling for the ones
  that are there.
- **Packaging and deployment.** There is no Dockerfile and no deployment path.

## Ordinary things

Fork, branch, and open a pull request against `main`.

```bash
python -m pip install -e ".[backoffice,test]"
python -m pytest
```

The suite runs in seconds, makes no network calls and costs nothing. CI runs it
on every push and pull request. Please keep it green, and add a test with a
behaviour change — the tests assert structural invariants rather than fixed
counts, so they hold for whichever task file is loaded.

Keep commits focused and explain *why* in the message, not just what.

If you find something wrong in a regulatory extract, that is a correctness bug
and worth an issue on its own, whether or not you have a fix.

## Security and disclosure

If you find something that should not be reported in public — a leaked
credential in the history, a real identifier that slipped into a task — email
`contact@schmittsfn.com` rather than opening an issue.

## Licence

Swissfin Bench is Apache-2.0. Under section 5 of that licence, anything you
deliberately submit for inclusion is contributed under the same terms, unless
you say otherwise. There is no separate contributor licence agreement.

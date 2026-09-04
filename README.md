# Swissfin Bench

A benchmark that tests large language models against Swiss financial regulatory
text, and scores them.

Stefan Schmitt — contact@schmittsfn.com

## The question this benchmark answers

On Swiss regulatory text, does this model carry out the instruction using the
document it was supplied with, does it confine itself to what that document
contains, and does it refuse to conclude when the document does not permit a
conclusion?

## What it does not do

1. It does not verify the compliance of any decision or activity.
2. It does not measure degree of compliance.

## Test families

| Family | Illustration | Risk type | Testing method | Scoring method |
|:-----|:------:|:------:|:------:|------:|
| Redaction | <img src="assets/redaction.png" alt="" width="200"/> | Data protection | Redaction of identifiers | Deterministic |
| Grounding | <img src="assets/grounding.png" alt="" width="200"/> | Accuracy | Passage attribution | Deterministic |
| Injection | <img src="assets/injection.png" alt="" width="200"/> | Operational security | Are hidden instructions followed | Deterministic |

## Paired tests for grounding

The bench does not score whether a model interprets correctly: it has no
authority to do so. It scores whether the model recognises if a passage settles
the question or not.

To this end the bench uses paired tests: for the same question, test A includes
the provision that carries the answer, whereas test B removes it. The expected
result for test B is that *this passage does not permit a conclusion*.

This measures whether the model stops or whether it manufactures a plausible
answer. It also tests whether the model answers from its training or whether it
read the document it was given.

<img src="assets/chart.jpg" alt="" height="200"/>

## Preliminary findings

These runs were made between 28 and 31 August 2026 over the whole 25-task set, before the public and unpublished sets were separated. They are preliminary: run counts differ between models, and the negative twins are only six distinct items. They are reported because of the pattern in the last column, not as a ranking.

| Model | Runs | Overall | On the negative twins |
|:--|--:|--:|--:|
| grok-4.20-0309 (non-reasoning) | 5 | 96.0% | 83.3% |
| gpt-5.6-sol | 5 | 88.8% | 53.3% |
| mistral-medium-latest | 5 | 88.0% | 50.0% |
| gemini-2.5-pro (Vertex AI) | 1 | 88.0% | 50.0% |
| gemma3:1b (local) | 5 | 34.4% | 0.0% |

**The last column is the finding.** Three of the four hosted models answer between 88 and 89 per cent of tasks correctly, and then get about half of the negative twins wrong: shown a passage from which the decisive provision has been removed, they assert that it answers the question regardless. The paired construction is what makes this visible, because the same models look strong on the positive halves. One model, grok-4.20 in its non-reasoning configuration, does not show the effect to the same extent.

`gemma3:1b` is included to show the floor: a one-billion-parameter local model never returns the negative verdict at all.

**Apertus is deliberately excluded from the table.** The build tested, `Apertus-8B-Instruct-2509-GGUF:Q4_K_M`, returned `{"verdict": "Partial"}` in 92 of 175 executions. The grounding verdict is binary, so a third answer is scored incorrect whatever its content, and the resulting 6.9 per cent measures compliance with the output format rather than legal reasoning. Reporting it as a score would misrepresent the model. Neither the full-precision build nor a corrected prompt has been tested.

Run counts must be equalised before any of this is treated as a comparison between models.

## Terms used

1. **Supplied document** — the single piece the model receives. There is never
   more than one per test. It is either an excerpt of public official text or a
   fictional company document.
2. **Instruction** — what the model is asked to do with the document. Three
   forms only:
   - answer a question by quoting the passage that carries the answer;
   - list certain elements present in the document;
   - transform the document, for example by masking the PII in it.

   An instruction never asks the model to appraise compliance, something no LLM
   should have the authority to decide.
3. **Expected result** — the right answer.

## Task data, and the two sets

`tasks/swissfin_public_sample_v0_1.yaml` is public: two grounding pairs, four redaction tasks and the six injection payloads. It is enough to run the pipeline end to end and to see exactly what a task looks like. A second set is not published.

The reason is narrower than it may appear. The regulatory extracts are official Swiss texts. They are public by definition and already sit in every large training corpus, and that is not a problem here, because this benchmark does not test whether a model knows Swiss regulation. It tests whether the model confines itself to the document it was given. A model that has memorised a circular, and then asserts that a passage answers a question whose decisive sentence was removed, is failing the paired test exactly as intended.

What cannot be public is the pairing of a task with its expected result. Once `expected_result` sits beside its extract in a repository that is crawled, a model can recall the label instead of reasoning to it, and the task measures nothing. That answer key is what the unpublished set protects, and it is the only thing it protects.

**The two sets are intended as an instrument rather than a wall.** Both are run, and a model scoring markedly higher on the public set than on the unpublished one would be exhibiting the size of its own contamination. Two conditions must hold before that comparison means anything, and neither holds yet. The sets have to be of comparable difficulty, established by construction from matched sources and task types rather than inferred from the scores themselves, which would be circular. And the public set has to be large enough for a difference to be distinguishable from noise, which at eight tasks it is not. Until both hold, the separation protects the answer key and nothing more.

Both files carry a canary identifier, so that inclusion in a training corpus can be detected afterwards.

Regulatory extracts carry their source reference and the date of the text quoted. **Every person, address, identifier, telephone number, IBAN and AVS number in the redaction tasks is fictional** and uses reserved placeholder ranges.

## Install and run

Python 3.12.4. Dependencies are declared in `pyproject.toml`. In an activated
virtual environment:

```bash
python -m pip install -e ".[backoffice,test]"
python -m pytest
```

The tests use temporary SQLite databases and mocked model responses. They make
no paid API calls.

To load the sample task set and run it against a local model:

```bash
export SWISSFIN_DB_PATH=results/reproduction.db
python app.py input tasks/swissfin_public_sample_v0_1.yaml
python app.py run ollama gemma3:1b
python -m streamlit run backoffice/app.py
```

See [Reproducibility](docs/REPRODUCIBILITY.md) for provider credentials, the
fresh-database procedure, provenance capture and the limits of determinism.
Runs against hosted providers consume paid API credits; the test suite and CI
never make model calls.

A convenience script wraps the same commands using the active environment's
`python`:

```bash
./scripts/run.sh install
./scripts/run.sh test
./scripts/run.sh backoffice
```

## Intended model coverage

The models below are the intended comparison set. Version numbers and
availability move quickly — check current releases before reading anything into
a published run.

| Name | Url | Open weight | Country |
|:-----|:-----|:------:|:------:|
| Apertus | https://apertus-ai.org | Yes | Switzerland |
| Magistral Medium | https://mistral.ai/news/magistral/ | No | France |
| SOOFI | https://www.soofi.info | Yes | Germany |
| Llama Maverick | https://ai.meta.com/blog/llama-4-multimodal-intelligence/ | Yes | United States |
| Kimi | https://www.kimi.com | Yes | China |
| Fable | https://www.anthropic.com/claude/fable | No | United States |
| GPT | https://openai.com/index/gpt-5-6/ | No | United States |

## Related benchmarks

| Entity | Repo | Licence | Maintainer | Country |
|:-----|:------|:------:|:------|:------:|
| finbenchmark.ai | https://github.com/gaschwanden/finbenchmark | MIT | [Gideon Aschwanden](https://www.linkedin.com/in/gideon-aschwanden/) | Switzerland |
| Financebenchmark.ai | https://github.com/Finance-Benchmark | None stated | [R. Obodugo](https://www.linkedin.com/in/obodugo/) | United States |
| Helvetic.ai | https://github.com/FUenal/swiss-bench | CC BY-NC-SA 4.0 | [Fatih Uenal](https://www.linkedin.com/in/fatih-uenal/) | Switzerland |

## References

- Ragas: Automated Evaluation of Retrieval Augmented Generation — https://arxiv.org/abs/2309.15217
- Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena — https://arxiv.org/abs/2306.05685
- G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment — https://arxiv.org/abs/2303.16634
- LLM01:2025 Prompt Injection — https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- Swiss-Bench SBP-002: A Frontier Model Comparison on Swiss Legal and Regulatory Tasks — https://arxiv.org/abs/2603.23646
- LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models — https://arxiv.org/abs/2308.11462
- Bolaji, Z., John, H. and Obodugo, R. (2026). Adversarial Consensus Verification for Reliable LLM Agents in Financial Forensics: The Pave Interchange Benchmark — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6944801
- Apertus: Democratizing Open and Compliant LLMs for Global Language Environments — https://arxiv.org/abs/2509.14233

## Glossary

**FINMA** — Switzerland's financial market regulator (Financial Market
Supervisory Authority; German: Eidgenössische Finanzmarktaufsicht). FINMA
Guidance 08/2024 does not create a certification regime for software. It sets
out governance and risk-management expectations: testing, monitoring,
documentation, explainability, independent review.

**FADP** — the Federal Act on Data Protection (German: Bundesgesetz über den
Datenschutz), Switzerland's primary data protection law and its counterpart to
the GDPR.

## Contributing

Contributions are welcome, and independent review of the existing tasks is the
most useful of all — every task currently reads `checked_by: pending
independent review`. German and Italian tasks are the biggest gap in what the
benchmark can claim, since each Swiss official language carries equal legal
authority.

One point to note before opening a pull request: a task becomes public the moment it appears in one, so it joins the public set rather than the scoring set. That is not a lesser outcome, and both routes accept tasks in any language. German and Italian tasks are wanted through both, because the scored set is French-only at present and public contributions alone cannot change that.

See [CONTRIBUTING.md](CONTRIBUTING.md) for what a good task looks like, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Licence

Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Stefan Schmitt.

Regulatory extracts reproduced in the task data are quoted from public FINMA
publications for the purpose of evaluation, with their source and date given in
each task.

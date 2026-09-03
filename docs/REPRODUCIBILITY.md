# Reproducibility

Swissfin Bench separates reproducible benchmark mechanics from model inference,
which can remain nondeterministic or change behind a provider alias.

## Python environment

The repository pins Python in `.python-version`. Direct runtime, backoffice, and
test dependency versions are pinned in `pyproject.toml`, which is the project's
single dependency source.

```bash
python -m pip install -e ".[backoffice,test]"
python --version
python -m pip check
python -m pytest
```

`pip` resolves transitive packages compatible with those direct pins. Because
the project intentionally has no separate lock file, a later installation can
select newer transitive packages. Record the actual installed environment with
each published result so that it can be audited:

```bash
mkdir -p results
python -m pip inspect > results/environment-inspect.json
```

## Reproduce against a fresh database

Never use the canonical `myfile.db` for an attempted reproduction. Select a new
path through `SWISSFIN_DB_PATH` or the CLI's `--database` option:

```bash
export SWISSFIN_DB_PATH=results/reproduction.db
python app.py input tasks/swissfin_public_sample_v0_1.yaml
```

The parent directory and SQLite schema are created automatically. Confirm the
loaded dataset before making model calls:

```bash
sqlite3 "$SWISSFIN_DB_PATH" \
  "SELECT family, expected_result, COUNT(*) FROM task_table GROUP BY family, expected_result;"
sqlite3 "$SWISSFIN_DB_PATH" "SELECT COUNT(*) FROM task_injection;"
shasum -a 256 tasks/swissfin_public_sample_v0_1.yaml
```

The canonical seed currently contains 12 grounding tasks in six positive/
negative pairs, 13 redaction tasks, six injections, and 72 task-injection links.
The automated dataset tests enforce these invariants.

The equivalent explicit-path form is:

```bash
python app.py \
  --database results/reproduction.db \
  input tasks/swissfin_public_sample_v0_1.yaml
```

## Run a model

A local Ollama run requires no API credential:

```bash
python app.py \
  --database results/reproduction.db \
  run ollama gemma3:1b
```

Remote runs can consume paid API credits. Export only the credential required by
the selected provider; `.env.example` lists the supported variable names but is
not loaded automatically and must never contain real secrets.

```bash
export MISTRAL_API_KEY="..."
python app.py \
  --database results/reproduction.db \
  run mistral mistral-medium-latest
```

```bash
export XAI_API_KEY="..."
python app.py \
  --database results/reproduction.db \
  run xai grok-4.20-0309-non-reasoning
```

For Vertex AI, configure Google Application Default Credentials and export the
project metadata instead of an API key:

```bash
gcloud auth application-default login
export VERTEXAI_PROJECT="your-project-id"
export VERTEXAI_LOCATION="global"
python app.py \
  --database results/reproduction.db \
  run vertex_ai gemini-2.5-pro \
  --label "gemini-2.5-pro (Vertex AI)"
```

Supported provider identifiers are printed when an invalid provider is passed to
`app.py run`. xAI grounding uses a forced function call because its endpoint does
not accept the benchmark's `response_format` schema directly.

The optional `--label` separates the provider's model identifier from the model
name stored in the results database. Rate limits, timeouts, and transient
connection failures use bounded backoff, with a 120-second request timeout by
default. Mistral requests are also paced at one-second intervals. Override these
only when the provider's documented quota permits it with
`SWISSFIN_REQUEST_TIMEOUT_SECONDS` or `SWISSFIN_MISTRAL_INTERVAL_SECONDS`.

## Inspect results

The backoffice reads the same `SWISSFIN_DB_PATH` variable:

```bash
export SWISSFIN_DB_PATH=results/reproduction.db
python -m streamlit run backoffice/app.py
```

## What is deterministic

- The version-controlled task text, expected results, pair structure, injections,
  grading rules, and score calculations are deterministic.
- Clean and injected requests ask for temperature `0`. If a model explicitly
  supports only its fixed default, the router retries without the unsupported
  parameter and logs that fallback in the run output.
- Grounding requests require a strict `Yes`, `No`, or `Partial` schema. xAI uses
  an equivalent forced function-call schema.
- Offline tests use fake model responses and make no network requests.

## What is not guaranteed to be deterministic

- Hosted providers can update a model behind an alias, change safety behavior, or
  route a request to different infrastructure.
- Temperature `0` reduces sampling variation but does not guarantee bit-for-bit
  identical inference across providers or hardware.
- A provider-fixed default temperature can introduce more sampling variation
  than a model that accepts temperature `0`; preserve the fallback log with the
  reported result.
- Not every provider accepts a portable random-seed parameter, so the benchmark
  does not pretend that one universal seed exists.
- Local Ollama reproduction also depends on the exact downloaded model digest and
  quantization, not only its display name.
- Historical labels containing `Codex headless` or `Claude headless` identify a
  transport-specific run. Reproducing one requires the same CLI transport and
  authenticated product tier, not merely an API model with a similar name.

## Provenance checklist

Record these alongside any reported result:

```bash
git rev-parse HEAD
shasum -a 256 pyproject.toml tasks/swissfin_public_sample_v0_1.yaml
python --version
python -m pip --version
python -m pip inspect > results/environment-inspect.json
```

Also retain the exact provider identifier, exact model identifier, database run
timestamp, local model digest and quantization where applicable, and any provider
rate-limit or retry event. A model alias such as `latest` is weaker provenance
than a dated or immutable model version.

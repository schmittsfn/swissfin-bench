from collections import Counter, defaultdict
from pathlib import Path

import yaml


SEED_PATH = Path(__file__).parents[1] / "tasks" / "swissfin_public_sample_v0_1.yaml"


def load_seed() -> dict:
    with SEED_PATH.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_seed_has_expected_benchmark_shape() -> None:
    """Shape invariants that must hold for any task file, sample or full set."""
    seed = load_seed()

    grounding = len(seed["grounding_task"])
    injections = len(seed["injection"])

    assert grounding > 0
    assert grounding % 2 == 0, "grounding tasks are paired, so the count is even"
    assert len(seed["redaction_task"]) > 0
    assert injections > 0
    assert len(seed["task_injection"]) == grounding * injections


def test_grounding_twins_are_symmetric_and_opposite() -> None:
    tasks = {task["id"]: task for task in load_seed()["grounding_task"]}
    unique_pairs: set[tuple[int, int]] = set()

    for task_id, task in tasks.items():
        twin_id = task["twin_task_id"]
        twin = tasks[twin_id]
        assert twin["twin_task_id"] == task_id
        assert twin["legal_query"] == task["legal_query"]
        assert {task["expected_result"], twin["expected_result"]} == {
            "SUCCESS",
            "FAILURE",
        }
        unique_pairs.add(tuple(sorted((task_id, twin_id))))

    assert len(unique_pairs) == len(tasks) // 2


def test_every_grounding_task_gets_each_injection_once() -> None:
    seed = load_seed()
    expected_injections = {injection["id"] for injection in seed["injection"]}
    links: dict[int, list[int]] = defaultdict(list)

    for link in seed["task_injection"]:
        links[link["task_id"]].append(link["injection_id"])

    assert set(links) == {task["id"] for task in seed["grounding_task"]}
    assert all(set(ids) == expected_injections for ids in links.values())
    assert all(len(ids) == len(expected_injections) for ids in links.values())


def test_task_content_required_by_graders_is_present() -> None:
    seed = load_seed()
    expected = Counter(task["expected_result"] for task in seed["grounding_task"])

    half = len(seed["grounding_task"]) // 2
    assert expected == Counter({"SUCCESS": half, "FAILURE": half})
    for task in seed["grounding_task"]:
        assert task["source_text_references"]
        assert task["source_text_extract"].strip()
        assert task["legal_query"].strip()

    for task in seed["redaction_task"]:
        assert isinstance(task["source_text_references"], list)
        assert task["source_document_text"].strip()
        assert task["terms_to_redact"]
        assert task["expected_result"] == "SUCCESS"

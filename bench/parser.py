from bench.schema import (
    Base, Note, Comparison, Task, GroundingTask, RedactionTask,
    Model, Execution, Injection
)
from typing import Any

from bench.database import Database


class Parser:
    def __init__(self, database: Database):
        self.database = database

    def parse(self, data: dict[str, Any]):
        """Parse a data dictionary and store it in the database."""
        print(f"Parsing data with keys: {list(data.keys())}")
        for key, value in data.items():
            print(f"Parsing section: {key}")
            if isinstance(value, list):
                for item in value:
                    self._parse_section(key, item)
            else:
                self._parse_section(key, value)
        print("Parsing complete.")

    def _parse_section(self, key: str, value: Any):
        if key == "redaction_task":
            self._parse_redaction_task(value)
        elif key == "grounding_task":
            self._parse_grounding_task(value)
        elif key == "injection":
            self._parse_injection(value)
        elif key == "task_injection":
            self._parse_task_injection(value)
        elif key == "model":
            self._parse_model(value)
        elif key == "execution":
            self._parse_execution(value)
        elif key == "note":
            self._parse_note(value)
        elif key == "comparison":
            self._parse_comparison(value)
        elif key == "comparison_note":
            self._parse_comparison_note(value)
        else:
            print(f"Unknown section '{key}', skipping.")

    def _parse_redaction_task(self, data: dict[str, Any]):
        if self.database.get_task_by_id(data["id"]):
            self.database.update_redaction_task(data["id"], data)
            print(f"Updated RedactionTask id={data['id']}")
        else:
            task = RedactionTask(
                id=data["id"],
                checked_by=data["checked_by"], status=data["status"],
                source_document_text=data["source_document_text"],
                terms_to_redact=data["terms_to_redact"], expected_result=data["expected_result"],
                source_text_references=data["source_text_references"],
            )
            self.database.add_task(task)
            print(f"Added RedactionTask id={task.id}")

    def _parse_grounding_task(self, data: dict[str, Any]):
        if self.database.get_task_by_id(data["id"]):
            self.database.update_grounding_task(data["id"], data)
            print(f"Updated GroundingTask id={data['id']}")
        else:
            task = GroundingTask(
                id=data["id"],
                checked_by=data["checked_by"], status=data["status"],
                source_text_extract=data["source_text_extract"],
                legal_query=data["legal_query"], expected_result=data["expected_result"],
                twin_task_id=data.get("twin_task_id"), source_text_references=data["source_text_references"],
            )
            self.database.add_task(task)
            print(f"Added GroundingTask id={task.id}")

    def _parse_injection(self, data: dict[str, Any]):
        if self.database.get_injection_by_id(data["id"]):
            self.database.update_injection(data["id"], data)
            print(f"Updated Injection id={data['id']}")
        else:
            inj = Injection(id=data["id"], injection_text=data["injection_text"])
            self.database.add_injection(inj)
            print(f"Added Injection id={inj.id}")

    def _parse_task_injection(self, data: dict[str, Any]):
        session = self.database._session
        task = session.get(Task, data["task_id"])
        inj = session.get(Injection, data["injection_id"])
        if task and inj and inj not in task.injections:
            task.injections.append(inj)
            self.database.commit()
            print(f"Linked task_id={data['task_id']} ↔ injection_id={data['injection_id']}")
        else:
            print(f"Skipping task_injection (not found or already linked): {data}")

    def _parse_model(self, data: dict[str, Any]):
        if self.database.get_model_by_id(data["id"]):
            self.database.update_model(data["id"], data)
            print(f"Updated Model id={data['id']}")
        else:
            model = Model(name=data["name"], quantization=data.get("quantization"))
            self.database.add_model(model)
            print(f"Added Model id={model.id}")

    def _parse_execution(self, data: dict[str, Any]):
        if self.database.get_execution_by_id(data["id"]):
            self.database.update_execution(data["id"], data)
            print(f"Updated Execution id={data['id']}")
        else:
            exe = Execution(task=data["task"], model=data["model"], timestamp=data["timestamp"])
            self.database.add_execution(exe)
            print(f"Added Execution id={exe.id}")

    def _parse_note(self, data: dict[str, Any]):
        if self.database.get_note_by_id(data["id"]):
            self.database.update_note(data["id"], data)
            print(f"Updated Note id={data['id']}")
        else:
            note = Note(execution=data["execution"], origin=data["origin"], score=data["score"])
            self.database.add_note(note)
            print(f"Added Note id={note.id}")

    def _parse_comparison(self, data: dict[str, Any]):
        if self.database.get_comparison_by_id(data["id"]):
            self.database.update_comparison(data["id"], data)
            print(f"Updated Comparison id={data['id']}")
        else:
            comparison = Comparison(similarity=data["similarity"])
            self.database.add_comparison(comparison)
            print(f"Added Comparison id={comparison.id}")

    def _parse_comparison_note(self, data: dict[str, Any]):
        session = self.database._session
        comparison = session.get(Comparison, data["comparison_id"])
        note = session.get(Note, data["note_id"])
        if comparison and note and note not in comparison.notes:
            comparison.notes.append(note)
            self.database.commit()
            print(f"Linked comparison_id={data['comparison_id']} ↔ note_id={data['note_id']}")
        else:
            print(f"Skipping comparison_note (not found or already linked): {data}")

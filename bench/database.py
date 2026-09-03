
from bench.schema import Base, Note, Comparison, Task, GroundingTask, RedactionTask, Model, Execution, Injection
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session
from typing import Any, Callable, TypeVar


T = TypeVar("T")

class Database:
    _engine: Any
    _session: Session
    path: Path | None

    def __init__(
        self,
        engine: Any | None = None,
        path: str | os.PathLike[str] | None = None,
    ):
        if engine is not None and path is not None:
            raise ValueError("Pass either engine or path, not both.")

        if engine is None:
            configured_path = path or os.environ.get("SWISSFIN_DB_PATH", "myfile.db")
            self.path = Path(configured_path).expanduser()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(
                URL.create("sqlite", database=str(self.path)),
                connect_args={"autocommit": False},
            )
        else:
            self.path = None

        self._engine = engine
        Base.metadata.create_all(self._engine)
        self._session = sessionmaker(bind=self._engine)()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        # fallback only, not primary lifecycle control
        try:
            self.close()
        except Exception:
            pass

    def commit(self):
        self._session.commit()

    def close(self):
        try:
            self._session.rollback()
        except Exception:
            pass
        try:
            self._session.close()
        except Exception:
            pass

    def _run_write(self, action: Callable[[Session], T]) -> T:
        if self._session.in_transaction():
            self._session.rollback()

        write_session = sessionmaker(bind=self._engine, expire_on_commit=False)()
        try:
            result = action(write_session)
            write_session.commit()
            return result
        except Exception:
            write_session.rollback()
            raise
        finally:
            write_session.close()

    def add(self, obj: Any):
        self._run_write(lambda s: s.add(obj))

    def get_all_tasks(self) -> list[Task]:
        return self._session.query(Task).all()

    def get_all_models(self) -> list[Model]:
        return self._session.query(Model).all()

    def get_all_injections(self) -> list[Injection]:
        return self._session.query(Injection).all()

    def get_all_executions(self) -> list[Execution]:
        return self._session.query(Execution).all()

    def get_all_notes(self) -> list[Note]:
        return self._session.query(Note).all()

    def get_notes_by_execution(self, execution_id: str) -> list[Note]:
        return self._session.query(Note).filter(Note.execution == execution_id).all()

    def get_task_by_id(self, task_id: str) -> Task | None:
        return self._session.get(Task, task_id)

    def add_task(self, task: Task, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(task))
        else:
            self._session.add(task)

    def update_grounding_task(self, task_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                task = s.get(GroundingTask, task_id)
                if task:
                    task.checked_by = data["checked_by"]
                    task.status = data["status"]
                    task.source_text_references = data["source_text_references"]
                    task.source_text_extract = data["source_text_extract"]
                    task.legal_query = data["legal_query"]
                    task.expected_result = data["expected_result"]
                    task.twin_task_id = data.get("twin_task_id")
                return task

            return self._run_write(_action)

        task = self._session.get(GroundingTask, task_id)
        if task:
            task.checked_by = data["checked_by"]
            task.status = data["status"]
            task.source_text_references = data["source_text_references"]
            task.source_text_extract = data["source_text_extract"]
            task.legal_query = data["legal_query"]
            task.expected_result = data["expected_result"]
            task.twin_task_id = data.get("twin_task_id")
        return task

    def update_redaction_task(self, task_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                task = s.get(RedactionTask, task_id)
                if task:
                    task.checked_by = data["checked_by"]
                    task.status = data["status"]
                    task.source_text_references = data["source_text_references"]
                    task.source_document_text = data["source_document_text"]
                    task.terms_to_redact = data["terms_to_redact"]
                    task.expected_result = data["expected_result"]
                return task

            return self._run_write(_action)

        task = self._session.get(RedactionTask, task_id)
        if task:
            task.checked_by = data["checked_by"]
            task.status = data["status"]
            task.source_text_references = data["source_text_references"]
            task.source_document_text = data["source_document_text"]
            task.terms_to_redact = data["terms_to_redact"]
            task.expected_result = data["expected_result"]
        return task

    def get_injection_by_id(self, injection_id: int) -> Injection | None:
        return self._session.get(Injection, injection_id)

    def add_injection(self, injection: Injection, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(injection))
        else:
            self._session.add(injection)

    def update_injection(self, injection_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                injection = s.get(Injection, injection_id)
                if injection:
                    injection.injection_text = data["injection_text"]
                return injection

            return self._run_write(_action)

        injection = self._session.get(Injection, injection_id)
        if injection:
            injection.injection_text = data["injection_text"]
        return injection

    def get_model_by_id(self, model_id: str) -> Model | None:
        return self._session.get(Model, model_id)

    def get_model_by_name(self, model_name: str) -> Model | None:
        return self._session.query(Model).filter(Model.name == model_name).first()

    def add_model(self, model: Model, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(model))
        else:
            self._session.add(model)

    def update_model(self, model_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                model = s.get(Model, model_id)
                if model:
                    model.name = data["name"]
                    model.quantization = data.get("quantization")
                return model

            return self._run_write(_action)

        model = self._session.get(Model, model_id)
        if model:
            model.name = data["name"]
            model.quantization = data.get("quantization")
        return model

    def get_execution_by_id(self, execution_id: str) -> Execution | None:
        return self._session.get(Execution, execution_id)

    def add_execution(self, execution: Execution, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(execution))
        else:
            self._session.add(execution)

    def update_execution(self, execution_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                execution = s.get(Execution, execution_id)
                if execution:
                    if "task_id" in data:
                        execution.task_id = data["task_id"]
                    if "model_id" in data:
                        execution.model_id = data["model_id"]
                    if "timestamp" in data:
                        execution.timestamp = data["timestamp"]
                return execution

            return self._run_write(_action)

        execution = self._session.get(Execution, execution_id)
        if execution:
            if "task_id" in data:
                execution.task_id = data["task_id"]
            if "model_id" in data:
                execution.model_id = data["model_id"]
            if "timestamp" in data:
                execution.timestamp = data["timestamp"]
        return execution

    def get_note_by_id(self, note_id: str) -> Note | None:
        return self._session.get(Note, note_id)

    def add_note(self, note: Note, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(note))
        else:
            self._session.add(note)

    def update_note(self, note_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                note = s.get(Note, note_id)
                if note:
                    note.execution = data["execution"]
                    note.origin = data["origin"]
                    note.score = data["score"]
                return note

            return self._run_write(_action)

        note = self._session.get(Note, note_id)
        if note:
            note.execution = data["execution"]
            note.origin = data["origin"]
            note.score = data["score"]
        return note

    def get_comparison_by_id(self, comparison_id: str) -> Comparison | None:
        return self._session.get(Comparison, comparison_id)

    def add_comparison(self, comparison: Comparison, commit: bool = True):
        if commit:
            self._run_write(lambda s: s.add(comparison))
        else:
            self._session.add(comparison)

    def update_comparison(self, comparison_id: int, data: dict, commit: bool = True):
        if commit:
            def _action(s: Session):
                comparison = s.get(Comparison, comparison_id)
                if comparison:
                    comparison.similarity = data["similarity"]
                return comparison

            return self._run_write(_action)

        comparison = self._session.get(Comparison, comparison_id)
        if comparison:
            comparison.similarity = data["similarity"]
        return comparison

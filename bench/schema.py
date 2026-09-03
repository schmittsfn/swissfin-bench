"""The schema module contains the schema definitions for the benchmark data models."""

from typing import Optional, Self, Literal, get_args, List
from sqlalchemy import Table, Column, Enum, Text, String, Date, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

from enum import Enum as PyEnum
from datetime import date

class TaskFamily(PyEnum):
    REDACTION = "task_fam_redaction"
    GROUNDING = "task_fam_grounding"

class EvaluationResult(PyEnum):
    SUCCESS = "eval_result_success"
    FAILURE = "eval_result_failure"
    PARTIAL_SUCCESS = "eval_result_partial_success"
    ERROR = "eval_result_error"

NOTE_DETERMINISTIC = "note_deterministic"
NOTE_JUDGE = "note_judge"

NoteOrigin = Literal[
    NOTE_DETERMINISTIC,
    NOTE_JUDGE
]

TASK_NOT_STARTED = "task_not_started"
TASK_IN_PROGRESS = "task_in_progress"
TASK_DONE = "task_done"

TaskStatus = Literal[
    TASK_NOT_STARTED,
    TASK_IN_PROGRESS,
    TASK_DONE
]

class Base(DeclarativeBase):
    """The base class"""

task_injection = Table(
    "task_injection",
    Base.metadata,
    Column("task_id", String, ForeignKey("task_table.id"), primary_key=True),
    Column("injection_id", String, ForeignKey("injection_table.id"), primary_key=True)
)

comparison_note = Table(
    "comparison_note",
    Base.metadata,
    Column("comparison_id", String, ForeignKey("comparison_table.id"), primary_key=True),
    Column("note_id", String, ForeignKey("note_table.id"), primary_key=True)
)

class Task(Base):
    """Represents a task in the benchmark."""
    __tablename__ = "task_table"
    __mapper_args__ = {"polymorphic_on": "family"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    family: Mapped[str] = mapped_column(String)

    checked_by: Mapped[str] = mapped_column(String)         # Tasks need to be signed-off by a human
    status: Mapped[str] = mapped_column(Enum(
        *get_args(TaskStatus),
        name="taskstatus",
        create_constraint=True,
        validate_strings=True,
    ))

    source_text_references: Mapped[list[str]] = mapped_column(JSON)  # References to the source text (law)

    injections: Mapped[List["Injection"]] = relationship(
        "Injection",
        secondary=task_injection,
        back_populates="tasks"
    )

    expected_result: Mapped[EvaluationResult] = mapped_column(Enum(
            EvaluationResult,
            name="expected_eval_result",
            create_constraint=True,
            validate_strings=True,
        ))

class GroundingTask(Task):
    """Represents a grounding task in the benchmark."""
    __tablename__ = "grounding_task_table"
    
    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("task_table.id"),
        primary_key=True,
        autoincrement=False
    )
    
    __mapper_args__ = {
        "polymorphic_identity": TaskFamily.GROUNDING.value
    }

    source_text_extract: Mapped[str] = mapped_column(Text)  # Extract from the source text (law)
    legal_query: Mapped[str] = mapped_column(Text)  # Reference to the grounding text (law)

    twin_task_id: Mapped[int | None] = mapped_column(ForeignKey("grounding_task_table.id"), nullable=True)  # Twin-task ID (reference to another GroundingTask)
    twin_task: Mapped[Optional["GroundingTask"]] = relationship(
        "GroundingTask",
        primaryjoin="GroundingTask.id==GroundingTask.twin_task_id",
        uselist=False,
        viewonly=True
    )

class RedactionTask(Task):
    """Represents a redaction task in the benchmark."""
    __tablename__ = "redaction_task_table"
    
    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("task_table.id"),
        primary_key=True,
        autoincrement=False
    )
    
    __mapper_args__ = {
        "polymorphic_identity": TaskFamily.REDACTION.value
    }

    source_document_text: Mapped[str] = mapped_column(Text)  # Source document to be redacted
    terms_to_redact: Mapped[list[str]] = mapped_column(JSON)  # Terms to be redacted from the source text

class Injection(Base):
    """Represents an injection task in the benchmark."""
    __tablename__ = "injection_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    injection_text: Mapped[str] = mapped_column(Text)  # Text to be injected into the source text

    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        secondary=task_injection,
        back_populates="injections"
    )

class Model(Base):
    """Represents a model used in the benchmark."""
    __tablename__ = "model_table"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)                                 # Name of the model
    quantization: Mapped[str | None] = mapped_column(String, nullable=True)   # Quantization of the model

class Execution(Base):
    """A run of a model on a task"""
    __tablename__ = "execution_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(ForeignKey("task_table.id")) # Each execution has a task tied to it
    task: Mapped[Task] = relationship("Task", backref="executions") # Relationship to the task

    model_id: Mapped[int] = mapped_column(ForeignKey("model_table.id")) # Each execution has a model tied to it
    model: Mapped[Model] = relationship("Model", backref="executions") # Relationship to the model

    timestamp: Mapped[str] = mapped_column(String) # The time the execution was run
    response: Mapped[str | None] = mapped_column(Text, nullable=True) # Response to the task
    
    evaluation_result: Mapped[EvaluationResult | None] = mapped_column(Enum(
                EvaluationResult,
                name="evaluation_result",
                create_constraint=True,
                validate_strings=True,
            ), nullable=True)
    injection_evaluation_results: Mapped[dict[int, EvaluationResult]] = mapped_column(JSON, nullable=True)  # Evaluation results for each injection

class Note(Base):
    """The result of an execution"""
    __tablename__ = "note_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    execution: Mapped[Execution] = mapped_column(ForeignKey("execution_table.id"))
    origin: Mapped[str] = mapped_column(Enum(       # Who produced the note (see NOTE_ORIGINS)
        *get_args(NoteOrigin),
        name="noteorigin",
        create_constraint=True,
        validate_strings=True,
    ))
    score: Mapped[str] = mapped_column(String)      # The score that was given to the execution

class Comparison(Base):
    """A comparison between two notes"""
    __tablename__ = "comparison_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    similarity: Mapped[float] = mapped_column(Float)                                    # Similarity score between two notes
    notes: Mapped[List["Note"]] = relationship(
        "Note",
        secondary=comparison_note,
    )

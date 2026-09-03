from bench.errors import ExecutionError, ModelSourceError


def test_benchmark_errors_preserve_their_messages() -> None:
    assert str(ExecutionError("execution failed")) == "execution failed"
    assert str(ModelSourceError("source failed")) == "source failed"

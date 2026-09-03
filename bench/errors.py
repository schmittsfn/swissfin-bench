class ModelSourceError(Exception):
    """Exception raised for errors in the model source."""
    def __init__(self, message="Invalid model source provided."):
        self.message = message
        super().__init__(self.message)


class ExecutionError(Exception):
    """Exception raised for errors during execution."""
    def __init__(self, message="An error occurred during execution."):
        self.message = message
        super().__init__(self.message)
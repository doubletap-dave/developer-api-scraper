import structlog

class Metrics:
    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def log_performance(self, operation: str, time_taken: float):
        self.logger.info(f"{operation} took {time_taken:.2f} seconds")

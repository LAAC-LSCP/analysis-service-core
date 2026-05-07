"""Logging utilities."""

import logging
from typing import Optional
from uuid import UUID


class Logger(logging.LoggerAdapter):
    """A logger that carries optional task and dataset context."""

    def __init__(
        self,
        logger: logging.Logger,
        task_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ):
        """Initialise a Logger, optionally binding task and dataset context."""
        super().__init__(logger, {})
        self._task_id = task_id
        self._dataset_id = dataset_id

    def process(self, msg, kwargs):
        """Prepend bound context fields to every log message."""
        parts = []
        if self._task_id:
            parts.append(f"task={self._task_id}")
        if self._dataset_id:
            parts.append(f"dataset={self._dataset_id}")
        if parts:
            return f"[{' '.join(parts)}] {msg}", kwargs
        return msg, kwargs

    def with_task(self, task_id: UUID | str) -> "Logger":
        """Return a new Logger with the given task ID bound."""
        return Logger(self.logger, task_id=str(task_id), dataset_id=self._dataset_id)

    def with_dataset(self, dataset_id: str) -> "Logger":
        """Return a new Logger with the given dataset ID bound."""
        return Logger(self.logger, task_id=self._task_id, dataset_id=dataset_id)


class LoggerFactory:
    """A factory that returns a logger standardized for the analysis service."""

    @staticmethod
    def get_logger(name: str, level: int = logging.INFO) -> Logger:
        """Returns a standardized logger instance for the given name.

        Example:
            logger = LoggerFactory.get_logger(__name__)
            logger.info("This is an info message.")

            task_logger = logger.with_task(task_id).with_dataset(dataset_id)
            task_logger.info("Processing.")  # [task=abc dataset=xyz] Processing.

        Args:
            name (str): The name of the logger, typically __name__.
            level (int): The logging level.

        Returns:
            Logger: Configured logger instance with builder methods.
        """
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(level)

        return Logger(logger)

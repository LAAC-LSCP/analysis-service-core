"""Logging utilities."""

import logging


class LoggerFactory:
    """A factory that returns a logger standardized for the analysis service."""

    @staticmethod
    def get_logger(name: str, level: int = logging.ERROR) -> logging.Logger:
        """Returns a standardized logger instance for the given name.

        Example:
            logger = LoggerFactory.get_logger(__name__)
            logger.info("This is an info message.")

        Args:
            name (str): The name of the logger, typically __name__.

        Returns:
            logging.Logger: Configured logger instance.
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

        return logger

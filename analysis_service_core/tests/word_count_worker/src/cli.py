import click

from analysis_service_core.src.config import Config
from analysis_service_core.src.redis.queue import Queue
from analysis_service_core.testing.models import WordCountEffortModel, WordCountModel


@click.command()
def run_word_count():
    """Run word count worker."""
    config = Config()
    queue = Queue("run_word_count")  # type: ignore[arg-type]
    effort_model = WordCountEffortModel(config)
    model = WordCountModel(
        queue=queue,
        config=config,
        effort_model=effort_model,
    )
    model.run()


if __name__ == "__main__":
    run_word_count()

FROM python:3.13-slim
WORKDIR /app

RUN pip install --no-cache-dir click redis pyyaml

COPY analysis_service_core/src ./analysis_service_core/src
COPY analysis_service_core/testing ./analysis_service_core/testing
COPY analysis_service_core/tests/word_count_worker/src ./src

ENV PYTHONPATH=/app

ENTRYPOINT ["python"]
CMD ["-m", "src.cli"]

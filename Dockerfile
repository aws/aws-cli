# syntax = docker/dockerfile:1.2
ARG DEFAULT_DOCKER_REPO
FROM ${DEFAULT_DOCKER_REPO}/python:3.9-slim

SHELL ["/bin/bash", "-c"]

COPY . /aws-cli
WORKDIR /aws-cli

RUN set -euo pipefail; \
  apt-get update; \
  apt-get install -y git; \
  pip install pip --upgrade;

RUN python scripts/ci/install; \
    python scripts/ci/install-check;

ENTRYPOINT ["aws"]

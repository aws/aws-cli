FROM python:3.6.5-alpine AS builder

WORKDIR /app

COPY requirements.txt .
RUN apk add --no-cache \
      --virtual git \
    && pip install -r requirements.txt \
    && apk del git

COPY . .
RUN pip install -e .

VOLUME /root/.aws

VOLUME /project
WORKDIR /project

ENTRYPOINT ["aws"]
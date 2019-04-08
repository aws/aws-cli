FROM alpine:3.6

RUN mkdir -p /awscli
COPY . /awscli

WORKDIR /

RUN apk --no-cache update && \
    apk --no-cache add python py-pip py-setuptools && \
    pip install --upgrade pip && \
    pip --no-cache-dir install -e /awscli/ && \
    rm -rf /var/cache/apk/*
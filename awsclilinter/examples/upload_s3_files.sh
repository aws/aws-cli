#!/bin/bash
# Example script with AWS CLI v1 patterns

aws secretsmanager put-secret-value --secret-id secret1213 \
  --secret-binary file://data.json

if
 aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json ; then
    echo "command succeeded."
fi

aws s3 ls s3://mybucket

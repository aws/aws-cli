#!/bin/bash
# Example script with AWS CLI v1 patterns

aws secretsmanager put-secret-value --secret-id secret1213 \
  --secret-binary file://data.json

if
 aws kinesis put-record --stream-name samplestream --data file://data --partition-key samplepartitionkey ; then
    echo "command succeeded."
fi

aws s3 ls s3://mybucket

aws ecr --debug get-login
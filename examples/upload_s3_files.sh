#!/bin/bash
# Example script with AWS CLI v1 patterns

TEMPLATE_FILE="$1"
BUCKET="$2"

'aws' secretsmanager put-secret-value --secret-id secret1213 \
  --secret-binary file://data.json

if
 aws kinesis put-record --stream-name samplestream --data file://data --partition-key samplepartitionkey ; then
    echo "command succeeded."
fi

aws s3 ls s3://mybucket

TEMPLATE_KEY="cloudformation/$(basename "$TEMPLATE_FILE")"

aws ecr --debug get-login --registry-ids "https://s3.amazonaws.com/"$BUCKET/01234

aws s3 ls --endpoint-url "https://s3.amazonaws.com/"

# Create a stack from the template
aws cloudformation create-stack \
  --stack-name "stack012345" \
  --template-body "https://s3.amazonaws.com/$BUCKET/$TEMPLATE_KEY" \
  --region "us-west-2"
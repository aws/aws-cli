#!/bin/bash
# Example script with AWS CLI v1 patterns

# TODO update examples to commands that specify file:// for blob-type params

# This command needs --cli-binary-format flag
aws s3api put-object --bucket mybucket --key mykey --body file://data.json

# This command also needs the flag
aws dynamodb put-item --table-name mytable --item file://item.json

# This command doesn't use file:// so it's fine
aws s3 ls s3://mybucket

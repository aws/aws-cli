**To permit the specified Amazon Web Services account or Amazon Web Services organization to put events to the specified event bus**

The following ``put-permission`` example permits the specified Amazon Web Services account or Amazon Web Services organization to put events to the specified event bus. ::

    aws events put-permission \
        --event-bus-name cli-test \
        --policy file://my-file.json

Contents of ``my-file.json``::

    {
      "Version": "2012-10-17",
      "Statement": [{
        "Sid": "allow_account_to_put_events",
        "Effect": "Allow",
        "Principal": {
          "AWS": ["arn:aws:iam::123123123123:root"]
        },
        "Action": "events:PutEvents",
        "Resource": "arn:aws:events:us-east-1:123456789012:event-bus/cli-test"
      }]
    }

This command produces no output.

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.
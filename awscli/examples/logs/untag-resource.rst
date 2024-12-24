**To Remove one or more tags from the specified resource.**

The following ``untag-resource`` example removes the tag with the key ``team`` from log group named ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs untag-resource \
        --resource-arn arn:aws:logs:us-east-1:123456789:log-group:demo-log-group \
        --tag-keys team

For more information, see `Working with log groups and log streams <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html>`__ in the *Amazon CloudWatch User Guide*.
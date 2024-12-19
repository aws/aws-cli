**To Create or update a subscription filter**

The following ``put-subscription-filter`` example creates a subscription filter for the log group ``demo-log-group``. If the command succeeds, no output is returned. ::

    aws logs put-subscription-filter \
        --log-group-name  "demo-log-group" \
        --filter-name "RootAccess" \
        --filter-pattern "{$.userIdentity.type = Root}" \
        --destination-arn "arn:aws:kinesis:us-east-1:123456789012:stream/DemoStream" \
        --role-arn "arn:aws:iam::123456789012:role/DemoCWLtoKinesisRole"

For more information, see `Real-time processing of log data with subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html>`__ in the *Amazon CloudWatch User Guide*.
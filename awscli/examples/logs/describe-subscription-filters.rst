**To List the subscription filters for the specified log group**

The following ``describe-subscription-filters`` example lists the subscription filters for the log group named ``demo-log-group``. ::

    aws logs describe-subscription-filters \
        --log-group-name demo-log-group

Output::

    {
        "subscriptionFilters": [
            {
                "filterName": "DemoSubscriptionFilter",
                "logGroupName": "demo-log-group",
                "filterPattern": "%AUTHORIZED%",
                "destinationArn": "arn:aws:lambda:us-east-1:123456789012:function:Lambda-Subscription-Filter",
                "distribution": "ByLogStream",
                "creationTime": 1698474178292
            }
        ]
    }

For more information, see `Real-time processing of log data with subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html>`__ in the *Amazon CloudWatch User Guide*.
**To Delete subscription filter**

The following ``delete-subscription-filter`` example deletes the subscription filter named ``demo-subscription-filter``. If the command succeeds, no output is returned. ::

    aws logs delete-subscription-filter \
        --log-group-name demo-log-group \
        --filter-name demo-subscription-filter

For more information, see `Real-time processing of log data with subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html>`__ in the *Amazon CloudWatch User Guide*.
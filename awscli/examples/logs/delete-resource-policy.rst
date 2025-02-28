**To delete a resource policy from the account**

The following ``delete-resource-policy`` example deletes the resource policy named ``demo-logs-policy`` from the account. ::

    aws logs delete-resource-policy \
        --policy-name "demo-logs-policy"

This command produces no output.

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
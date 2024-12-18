**To Delete a resource policy from the account**

The following ``delete-resource-policy`` example deletes the resource policy named ``demo-logs-policy`` from the account. If the command succeeds, no output is returned. ::

    aws logs delete-resource-policy \
        --policy-name "demo-logs-policy"

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
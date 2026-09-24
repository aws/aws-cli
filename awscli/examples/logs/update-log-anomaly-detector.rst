**To update a log anomaly detector**

The following ``update-log-anomaly-detector`` example updates evaluation frequency of a log anomaly detector to ONE_HOUR. ::

    aws logs update-log-anomaly-detector \
        --anomaly-detector-arn arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111 \
        --evaluation-frequency="ONE_HOUR" \
        --enabled

This command produces no output.

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
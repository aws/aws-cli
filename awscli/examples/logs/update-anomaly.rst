**To Suppress anomaly detection**

The following ``update-anomaly`` example suppress anomaly detection for a specified anomaly or pattern. If the command succeeds, no output is returned. ::

    aws logs update-anomaly \
        --anomaly-detector-arn arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111 \
        --anomaly-id a1b2c3d4-5678-90ab-cdef-example12345 \
        --suppression-type LIMITED \
        --suppression-period value=60,suppressionUnit=SECONDS

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
**To Delete an anomaly detector**

The following ``delete-log-anomaly-detector`` example deletes an anomaly detector named ``demo_anomaly_detector``. If the command succeeds, no output is returned. ::

    aws logs delete-log-anomaly-detector \
        --anomaly-detector-arn arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
**To Create an anomaly detector**

The following ``create-log-anomaly-detector`` example creates an anomaly detector named ``demo_anomaly_detector``. ::

    aws logs create-log-anomaly-detector \
        --log-group-arn-list arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group \
        --detector-name demo_anomaly_detector

Output::

    {
        "anomalyDetectorArn": "arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111"
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
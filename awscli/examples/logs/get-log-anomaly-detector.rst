**To Retrieve information about a log anomaly detector**

The following ``get-log-anomaly-detector`` example retrieves information about a log anomaly detector. ::

    aws logs get-log-anomaly-detector \
        --anomaly-detector-arn arn:aws:logs:us-east-1:123456789012:anomaly-detector:b52e46a3-e66d-43bc-9b96-bb16d305cd42

Output::

    {
        "detectorName": "demo_anomaly_detector",
        "logGroupArnList": [
            "arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group"
        ],
        "evaluationFrequency": "FIVE_MIN",
        "anomalyDetectorStatus": "TRAINING",
        "creationTimeStamp": 1729218987707,
        "lastModifiedTimeStamp": 1729218987992,
        "anomalyVisibilityTime": 7
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
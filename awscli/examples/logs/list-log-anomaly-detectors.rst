**To Retrieve a list of log anomaly detectors**

The following ``list-log-anomaly-detectors`` example retrieves a list of log anomaly detectors in the account. ::

    aws logs list-log-anomaly-detectors

Output::

    {
        "anomalyDetectors": [
            {
                "anomalyDetectorArn": "arn:aws:logs:us-east-1:123456789012:anomaly-detector:a1b2c3d4-5678-90ab-cdef-example11111",
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
        ]
    }

For more information, see `Log anomaly detection <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html>`__ in the *Amazon CloudWatch Logs User Guide*.
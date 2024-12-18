**To describe an observation from an application**

This example uses the ``describe-observation`` command to describe an observation such as an anomaly or error in the application. ::

    aws application-insights describe-observation \
        --observation-id o-1aaaf123-abc4-5678-a12e-d01234e56d7e

Output::

    {
        "Observation": {
            "Id": "o-1aaaf123-abc4-5678-a12e-d01234e56d7e",
            "StartTime": "2024-01-01T02:05:55.432000+00:00",
            "EndTime": "2024-01-01T02:12:55.435000+00:00",
            "SourceType": "ALARM",
            "SourceARN": "arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56",
            "MetricNamespace": "AWS/EC2",
            "MetricName": "CPUUtilization",
            "Value": 99.0208333333334
        }
    }
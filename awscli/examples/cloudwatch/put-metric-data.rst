**Example 1: To publish a custom metric to Amazon CloudWatch**

The following ``put-metric-data`` example publishes a custom metric to Amazon CloudWatch. ::

    aws cloudwatch put-metric-data \
        --namespace "Usage Metrics" \
        --metric-data file://metric.json

Contents of ``metric.json``::

    [
        {
            "MetricName": "New Posts",
            "Timestamp": "Wednesday, June 12, 2013 8:28:20 PM",
            "Value": 0.50,
            "Unit": "Count"
        }
    ]

This command produces no output.

For more information, see `Publish custom metrics (PutMetricData / EMF) <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html>`__ in the *Amazon CloudWatch User Guide*.

**Example 2: To specify multiple dimensions**

The following ``put-metric-data`` example illustrates how to specify multiple dimensions. Each dimension is specified as a Name=Value pair. Multiple dimensions are separated by a comma. ::

    aws cloudwatch put-metric-data \
        --metric-name Buffers \
        --namespace MyNameSpace \
        --unit Bytes \
        --value 231434333 \
        --dimensions InstanceID=1-23456789,InstanceType=m1.small

This command produces no output.

For more information, see `Metrics concepts <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html>`__ in the *Amazon CloudWatch User Guide*.

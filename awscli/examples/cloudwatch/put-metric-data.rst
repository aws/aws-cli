**To publish a custom metric to Amazon CloudWatch**

The following example uses the ``put-metric-data`` command to publish a custom metric to Amazon CloudWatch::

  aws cloudwatch put-metric-data --namespace "Usage Metrics" --metric-data file://metric.json

The values for the metric itself are stored in the JSON file, ``metric.json``.

Here are the contents of that file::

  [
    {
      "metric_name": "New Posts",
      "timestamp": "Wednesday, June 12, 2013 8:28:20 PM",
      "value": 0.50,
      "unit": "Count"
    }
  ]

For more information, see `Publishing Custom Metrics`_ in the *Amazon CloudWatch Developer Guide*.

.. _`Publishing Custom Metrics`: http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/publishingMetrics.html



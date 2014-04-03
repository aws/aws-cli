**To get the CPU utilization per EC2 instance**

The following example uses the ``get-metric-statistics`` command to get the CPU utilization per EC2
instance. For more examples using the ``get-metric-statistics`` command, see `Get Statistics for a Metric`_ in the *Amazon CloudWatch Developer Guide*.

.. _`Get Statistics for a Metric`: http://docs.aws.amazon.com/AmazonCloudWatch/latest/DeveloperGuide/US_GetStatistics.html::

  aws cloudwatch get-metric-statistics --metric-name CPUUtilization --start-time 2014-02-18T23:18:00 --end-time 2014-02-19T23:18:00 --period 3600 --namespace AWS/EC2 --statistics Maximum --dimensions Name=InstanceId,Value=YourInstanceID

Output::

  {
    "Label": "CPUUtilization",
    "Datapoints": [
      {
        "Timestamp": "2014-02-19T00:18:00Z",
        "Maximum": 0.33,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T03:18:00Z",
        "Maximum": 99.67,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T07:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T12:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T02:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T01:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T17:18:00Z",
        "Maximum": 3.39,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T13:18:00Z",
        "Maximum": 0.33,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-18T23:18:00Z",
        "Maximum": 0.67,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T06:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T11:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T10:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T19:18:00Z",
        "Maximum": 8.0,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T15:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T14:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T16:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T09:18:00Z",
        "Maximum": 0.34,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T04:18:00Z",
        "Maximum": 2.0,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T08:18:00Z",
        "Maximum": 0.68,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T05:18:00Z",
        "Maximum": 0.33,
        "Unit": "Percent"
      },
      {
        "Timestamp": "2014-02-19T18:18:00Z",
        "Maximum": 6.67,
        "Unit": "Percent"
      }
    ]
  }


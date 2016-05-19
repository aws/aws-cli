**To describe the Auto Scaling metric collection types**

This example describes the available metric collection types::

    aws autoscaling describe-metric-collection-types

The following is example output::

    {
        "Metrics": [
            {
                "Metric": "GroupMinSize"
            },
            {
                "Metric": "GroupMaxSize"
            },
            {
                "Metric": "GroupDesiredCapacity"
            },
            {
                "Metric": "GroupInServiceInstances"
            },
            {
                "Metric": "GroupPendingInstances"
            },
            {
                "Metric": "GroupTerminatingInstances"
            },
            {
                "Metric": "GroupTotalInstances"
            }
        ],
        "Granularities": [
            {
                "Granularity": "1Minute"
            }
        ]
    }

For more information, see `Enable Auto Scaling Group Metrics`_ in the *Auto Scaling Developer Guide*.

.. _`Enable Auto Scaling Group Metrics`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html#as-group-metrics

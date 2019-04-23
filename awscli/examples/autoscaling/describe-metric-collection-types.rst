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
                "Metric": "GroupStandbyInstances"
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

For more information, see `Auto Scaling Group Metrics`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Auto Scaling Group Metrics`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html#as-group-metrics

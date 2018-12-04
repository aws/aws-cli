**To describe the Auto Scaling adjustment types**

This example describes the available adjustment types::

    aws autoscaling describe-adjustment-types

The following is example output::

    {
        "AdjustmentTypes": [
            {
                "AdjustmentType": "ChangeInCapacity"
            },
            {
                "AdjustmentType": "ExactCapcity"
            },
            {
                "AdjustmentType": "PercentChangeInCapacity"
            }
        ]
    }

For more information, see `Scaling Adjustment Types`_ in the *Auto Scaling Developer Guide*.

.. _`Scaling Adjustment Types`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html#as-scaling-adjustment

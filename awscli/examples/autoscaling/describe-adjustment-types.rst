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

For more information, see `Scaling Adjustment Types`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Scaling Adjustment Types`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-simple-step.html#as-scaling-adjustment

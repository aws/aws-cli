**To describe the available scaling adjustment types**

This example describes the available adjustment types. ::

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

For more information, see `Scaling adjustment types <https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-simple-step.html#as-scaling-adjustment>`__ in the *Amazon EC2 Auto Scaling User Guide*.

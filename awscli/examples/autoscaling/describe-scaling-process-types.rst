**To describe the Auto Scaling process types**

This example describes the Auto Scaling process types::

    aws autoscaling describe-scaling-process-types

The following is example output::

    {
        "Processes": [
            {
                "ProcessName": "AZRebalance"
            },
            {
                "ProcessName": "AddToLoadBalancer"
            },
            {
                "ProcessName": "AlarmNotification"
            },
            {
                "ProcessName": "HealthCheck"
            },
            {
                "ProcessName": "Launch"
            },
            {
                "ProcessName": "ReplaceUnhealthy"
            },
            {
                "ProcessName": "ScheduledActions"
            },
            {
                "ProcessName": "Terminate"
            }
        ]
    }

For more information, see `Suspending and Resuming Scaling Processes`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Suspending and Resuming Scaling Processes`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-suspend-resume-processes.html

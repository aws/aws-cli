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

For more information, see `Suspend and Resume Auto Scaling Processes`_ in the *Auto Scaling Developer Guide*.

.. _`Suspend and Resume Auto Scaling Processes`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_SuspendResume.html

**Example 1: To describe scaling activities for the specified Amazon ECS service**

The following ``describe-scaling-activities`` example describes the scaling activities for an Amazon ECS service called ``web-app`` that is running in the ``default`` cluster. The output shows a scaling activity initiated by a scaling policy. ::

    aws application-autoscaling describe-scaling-activities \
        --service-namespace ecs \
        --resource-id service/default/web-app

Output::

    {
        "ScalingActivities": [
            {
                "ScalableDimension": "ecs:service:DesiredCount",
                "Description": "Setting desired count to 1.",
                "ResourceId": "service/default/web-app",
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "StartTime": 1462575838.171,
                "ServiceNamespace": "ecs",
                "EndTime": 1462575872.111,
                "Cause": "monitor alarm web-app-cpu-lt-25 in state ALARM triggered policy web-app-cpu-lt-25",
                "StatusMessage": "Successfully set desired count to 1. Change successfully fulfilled by ecs.",
                "StatusCode": "Successful"
            }
        ]
    }

For more information, see `Scaling activities for Application Auto Scaling <https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-scaling-activities.html>`__ in the *Application Auto Scaling User Guide*.

**Example 2: To describe scaling activities for the specified DynamoDB table**

The following ``describe-scaling-activities`` example describes the scaling activities for a DynamoDB table called ``TestTable``. The output shows scaling activities initiated by two different scheduled actions. ::

    aws application-autoscaling describe-scaling-activities \
        --service-namespace dynamodb \
        --resource-id table/TestTable

Output::

    {
        "ScalingActivities": [
            {
                "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
                "Description": "Setting write capacity units to 10.",
                "ResourceId": "table/my-table",
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "StartTime": 1561574415.086,
                "ServiceNamespace": "dynamodb",
                "EndTime": 1561574449.51,
                "Cause": "maximum capacity was set to 10",
                "StatusMessage": "Successfully set write capacity units to 10. Change successfully fulfilled by dynamodb.",
                "StatusCode": "Successful"
            },
            {
                "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
                "Description": "Setting min capacity to 5 and max capacity to 10",
                "ResourceId": "table/my-table",
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "StartTime": 1561574414.644,
                "ServiceNamespace": "dynamodb",
                "Cause": "scheduled action name my-second-scheduled-action was triggered",
                "StatusMessage": "Successfully set min capacity to 5 and max capacity to 10",
                "StatusCode": "Successful"
            },
            {
                "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
                "Description": "Setting write capacity units to 15.",
                "ResourceId": "table/my-table",
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "StartTime": 1561574108.904,
                "ServiceNamespace": "dynamodb",
                "EndTime": 1561574140.255,
                "Cause": "minimum capacity was set to 15",
                "StatusMessage": "Successfully set write capacity units to 15. Change successfully fulfilled by dynamodb.",
                "StatusCode": "Successful"
            },
            {
                "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
                "Description": "Setting min capacity to 15 and max capacity to 20",
                "ResourceId": "table/my-table",
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "StartTime": 1561574108.512,
                "ServiceNamespace": "dynamodb",
                "Cause": "scheduled action name my-first-scheduled-action was triggered",
                "StatusMessage": "Successfully set min capacity to 15 and max capacity to 20",
                "StatusCode": "Successful"
            }
        ]
    }

For more information, see `Scaling activities for Application Auto Scaling <https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-scaling-activities.html>`__ in the *Application Auto Scaling User Guide*.

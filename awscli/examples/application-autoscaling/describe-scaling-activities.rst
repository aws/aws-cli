**To describe scaling activities for a scalable target**

This example describes the scaling activities for an Amazon ECS service called `web-app` that is running in the `default` cluster.

Command::

  aws application-autoscaling describe-scaling-activities --service-namespace ecs --scalable-dimension ecs:service:DesiredCount --resource-id service/default/web-app

Output::

  {
    "ScalingActivities": [
      {
        "ScalableDimension": "ecs:service:DesiredCount",
        "Description": "Setting desired count to 1.",
        "ResourceId": "service/default/web-app",
        "ActivityId": "e6c5f7d1-dbbb-4a3f-89b2-51f33e766399",
        "StartTime": 1462575838.171,
        "ServiceNamespace": "ecs",
        "EndTime": 1462575872.111,
        "Cause": "monitor alarm web-app-cpu-lt-25 in state ALARM triggered policy web-app-cpu-lt-25",
        "StatusMessage": "Successfully set desired count to 1. Change successfully fulfilled by ecs.",
        "StatusCode": "Successful"
      }
    ]
  }
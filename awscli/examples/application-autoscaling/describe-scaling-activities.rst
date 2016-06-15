**To deregister a scalable target**

This example deregisters a scalable target for an Amazon ECS service called `web-app` that is running in the `default` cluster.

Command::

  aws application-autoscaling deregister-scalable-target --service-namespace ecs --scalable-dimension ecs:service:DesiredCount --resource-id service/default/web-app

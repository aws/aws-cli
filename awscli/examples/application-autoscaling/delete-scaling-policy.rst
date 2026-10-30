**To delete a scaling policy**

The following ``delete-scaling-policy`` example deletes a scaling policy for the Amazon ECS service `web-app` running in the `default` cluster. ::

    aws application-autoscaling delete-scaling-policy --policy-name web-app-cpu-lt-25 --scalable-dimension ecs:service:DesiredCount --resource-id service/default/web-app --service-namespace ecs

**To create or update tags for an Auto Scaling group**

This example adds two tags to the specified Auto Scaling group::

    aws autoscaling create-or-update-tags --tags ResourceId=my-auto-scaling-group,ResourceType=auto-scaling-group,Key=Role,Value=WebServer,PropagateAtLaunch=true ResourceId=my-auto-scaling-group,ResourceType=auto-scaling-group,Key=Dept,Value=Research,PropagateAtLaunch=true

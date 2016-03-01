**To complete the lifecycle action**

This example notifies Auto Scaling that the specified lifecycle action is complete so that it can finish launching or terminating the instance::

    aws autoscaling complete-lifecycle-action --lifecycle-hook-name my-lifecycle-hook --auto-scaling-group-name my-auto-scaling-group --lifecycle-action-result CONTINUE --lifecycle-action-token bcd2f1b8-9a78-44d3-8a7a-4dd07d7cf635

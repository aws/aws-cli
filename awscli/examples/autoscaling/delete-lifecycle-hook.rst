**To delete a lifecycle hook**

The following ``delete-lifecycle-hook`` example deletes the specified lifecycle hook. ::

    aws autoscaling delete-lifecycle-hook \
        --lifecycle-hook-name my-lifecycle-hook \
        --auto-scaling-group-name my-asg

This command produces no output.
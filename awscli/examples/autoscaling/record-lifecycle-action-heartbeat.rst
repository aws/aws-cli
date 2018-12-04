**To record a lifecycle action heartbeat**

This example records a lifecycle action heartbeat to keep the instance in a pending state::

    aws autoscaling record-lifecycle-action-heartbeat --lifecycle-hook-name my-lifecycle-hook --auto-scaling-group-name my-auto-scaling-group --lifecycle-action-token bcd2f1b8-9a78-44d3-8a7a-4dd07d7cf635

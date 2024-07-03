**Example 1: To pause running until a task is confirmed to be running**

The following ``wait`` example pauses and continues only after the specified task enters a ``RUNNING`` state. ::

    aws ecs wait tasks-running \
        --cluster MyCluster \
        --tasks arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-44444EXAMPLE
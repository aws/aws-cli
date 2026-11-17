**To pause running until a task is confirmed to be running**

The following ``wait tasks-running`` example pauses and continues only after the specified task enters a ``RUNNING`` state. ::

    aws ecs wait tasks-running \
        --cluster MyCluster \
        --tasks arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444

This command produces no output.

For more information, see `Amazon ECS task lifecycle <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html>`__ in the *Amazon ECS Developer Guide*.

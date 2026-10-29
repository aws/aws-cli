**Example 1: To pause running until a service is confirmed to be stable**

The following ``wait services-stable`` example pauses and continues only after it can confirm that the specified service running on the specified cluster is stable. ::

    aws ecs wait services-stable \
        --cluster MyCluster \
        --services MyService

This command produces no output.

For more information, see `Amazon ECS services <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To pause running until a task is confirmed to be running**

The following ``wait services-stable`` example pauses and continues only after the specified task enters a ``RUNNING`` state. ::

    aws ecs wait services-stable \
        --cluster MyCluster \
        --tasks arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444

This command produces no output.

For more information, see `Amazon ECS task lifecycle <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-explanation.html>`__ in the *Amazon ECS Developer Guide*.

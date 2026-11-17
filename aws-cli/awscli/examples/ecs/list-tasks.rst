**Example 1: To list the tasks in a cluster**

The following ``list-tasks`` example lists all of the tasks in a cluster. ::

    aws ecs list-tasks \
        --cluster default

Output::

    {
        "taskArns": [
            "arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        ]
    }

For more information, see `Amazon ECS task definitions <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To list the tasks on a particular container instance**

The following ``list-tasks`` example lists the tasks on a container instance, using the container instance UUID as a filter. ::

    aws ecs list-tasks \
        --cluster default \
        --container-instance a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "taskArns": [
            "arn:aws:ecs:us-west-2:123456789012:task/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
        ]
    }

For more information, see `Amazon ECS task definitions <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html>`__ in the *Amazon ECS Developer Guide*.

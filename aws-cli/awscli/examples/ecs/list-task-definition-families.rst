**Example 1: To list the registered task definition families**

The following ``list-task-definition-families`` example lists all of the registered task definition families. ::

    aws ecs list-task-definition-families

Output::

    {
        "families": [
            "node-js-app",
            "web-timer",
            "hpcc",
            "hpcc-c4-8xlarge"
        ]
    }

For more information, see `Amazon ECS task definition parameters for Fargate <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#family>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To filter the registered task definition families**

The following ``list-task-definition-families`` example lists the task definition revisions that start with "hpcc". ::

    aws ecs list-task-definition-families \
        --family-prefix hpcc

Output::

    {
        "families": [
            "hpcc",
            "hpcc-c4-8xlarge"
        ]
    }

For more information, see `Amazon ECS task definition parameters for Fargate <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#family>`__ in the *Amazon ECS Developer Guide*.

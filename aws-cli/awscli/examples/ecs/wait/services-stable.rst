**To pause running until a service is confirmed to be stable**

The following ``wait services-stable`` example pauses and continues only after it can confirm that the specified service running on the specified cluster is stable. ::

    aws ecs wait services-stable \
        --cluster MyCluster \
        --services MyService

This command produces no output.

For more information, see `Amazon ECS services <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html>`__ in the *Amazon ECS Developer Guide*.

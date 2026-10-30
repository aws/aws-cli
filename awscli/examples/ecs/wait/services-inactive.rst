**To wait until an ECS service becomes inactive**

The following ``wait services-inactive`` example waits until ECS services becomes inactive in the cluster. ::

    aws ecs wait services-inactive \
        --cluster MyCluster \
        --services MyService 

This command produces no output.

For more information, see `Amazon ECS services <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html>`__ in the *Amazon ECS Developer Guide*.

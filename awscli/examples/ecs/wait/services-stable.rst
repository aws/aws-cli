**Example 1: To pause running until a service is confirmed to be stable**

The following ``wait`` example pauses and continues only after it can confirm that the specified service running on the specified cluster is stable. There is no output. ::

    aws ecs wait services-stable \
        --cluster MyCluster \
        --services MyService
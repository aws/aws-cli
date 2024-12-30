**Get the endpoint for ECS agent for polling updates**

The following ``discover-poll-endpoint`` example returns the endpoint for the ECS agent to poll for the updates. You can pass container instance ID or full ARN of container instances. This example uses ID of the container instance. ::

    aws ecs discover-poll-endpoint \
        --container-instance d5f596ccb5794833b778c680c318ft78 \
        --cluster-name MyCluster

Output::

    {
    "endpoint": "https://ecs-a-16.us-west-2.amazonaws.com/",
    "telemetryEndpoint": "https://ecs-t-16.us-west-2.amazonaws.com/",
    "serviceConnectEndpoint": "https://ecs-sc.us-west-2.api.aws"
    }

For more information on Agent Endpoints, see `Create VPC Endpoints for Amazon ECS <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/vpc-endpoints.html#ecs-setting-up-vpc-create>`__ in the *Amazon ECS Developer Guide*. 
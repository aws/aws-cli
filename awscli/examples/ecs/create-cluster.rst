**Example 1: To create a new cluster**

The following ``create-cluster`` example creates a cluster named ``MyCluster`` and enables CloudWatch Container Insights with enhanced observability. ::

    aws ecs create-cluster \
        --cluster-name MyCluster \
        --settings name=containerInsights,value=enhanced


Output::

    {
        "cluster": {
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
            "clusterName": "MyCluster",
            "status": "ACTIVE",
            "registeredContainerInstancesCount": 0,
            "pendingTasksCount": 0,
            "runningTasksCount": 0,
            "activeServicesCount": 0,
            "statistics": [],
            "settings": [
                {
                    "name": "containerInsights",
                    "value": "enhanced"
                }
            ],
            "tags": []
        }
    }

For more information, see `Creating an Amazon ECS cluster for Fargate workloads <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-cluster-console-v2.html>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To create a new cluster using capacity providers**

The following ``create-cluster`` example creates a cluster and associates two existing capacity providers with it. The ``create-capacity-provider`` command is used to create a capacity provider. Specifying a default capacity provider strategy is optional, but recommended. In this example, we create a cluster named ``MyCluster`` and associate the ``MyCapacityProvider1`` and ``MyCapacityProvider2`` capacity providers with it. A default capacity provider strategy is specified that spreads the tasks evenly across both capacity providers. ::

    aws ecs create-cluster \
        --cluster-name MyCluster \
        --capacity-providers MyCapacityProvider1 MyCapacityProvider2 \
        --default-capacity-provider-strategy capacityProvider=MyCapacityProvider1,weight=1 capacityProvider=MyCapacityProvider2,weight=1

Output::

    {
        "cluster": {
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
            "clusterName": "MyCluster",
            "status": "PROVISIONING",
            "registeredContainerInstancesCount": 0,
            "pendingTasksCount": 0,
            "runningTasksCount": 0,
            "activeServicesCount": 0,
            "statistics": [],
            "settings": [
                {
                    "name": "containerInsights",
                    "value": "enabled"
                }
            ],
            "capacityProviders": [
                "MyCapacityProvider1",
                "MyCapacityProvider2"
            ],
            "defaultCapacityProviderStrategy": [
                {
                    "capacityProvider": "MyCapacityProvider1",
                    "weight": 1,
                    "base": 0
                },
                {
                    "capacityProvider": "MyCapacityProvider2",
                    "weight": 1,
                    "base": 0
                }
            ],
            "attachments": [
                {
                    "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "type": "asp",
                    "status": "PRECREATED",
                    "details": [
                        {
                            "name": "capacityProviderName",
                            "value": "MyCapacityProvider1"
                        },
                        {
                            "name": "scalingPlanName",
                            "value": "ECSManagedAutoScalingPlan-a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                        }
                    ]
                },
                {
                    "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                    "type": "asp",
                    "status": "PRECREATED",
                    "details": [
                        {
                            "name": "capacityProviderName",
                            "value": "MyCapacityProvider2"
                        },
                        {
                            "name": "scalingPlanName",
                            "value": "ECSManagedAutoScalingPlan-a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                        }
                    ]
                }
            ],
            "attachmentsStatus": "UPDATE_IN_PROGRESS"
        }
    }

For more information, see `Amazon ECS capacity providers for EC2 workloads <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/asg-capacity-providers.html>`__ in the *Amazon ECS Developer Guide*.

**Example 3: To create a new cluster with multiple tags**

The following ``create-cluster`` example creates a cluster with multiple tags.  For more information about adding tags using shorthand syntax, see `Using Shorthand Syntax with the AWS Command Line Interface <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-shorthand.html>`__ in the *AWS CLI User Guide*. ::

    aws ecs create-cluster \
        --cluster-name MyCluster \
        --tags key=key1,value=value1 key=key2,value=value2

Output::

    {
        "cluster": {
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
            "clusterName": "MyCluster",
            "status": "ACTIVE",
            "registeredContainerInstancesCount": 0,
            "pendingTasksCount": 0,
            "runningTasksCount": 0,
            "activeServicesCount": 0,
            "statistics": [],
            "tags": [
                {
                    "key": "key1",
                    "value": "value1"
                },
                {
                    "key": "key2",
                    "value": "value2"
                }
            ]
        }
    }

For more information, see `Creating an Amazon ECS cluster for Fargate workloads <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-cluster-console-v2.html>`__ in the *Amazon ECS Developer Guide*.

**Example 1: To create a new cluster**

The following ``create-cluster`` example creates a cluster. ::

    aws ecs create-cluster --cluster-name MyCluster

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
            "tags": []
        }
    }

**Example 2: To create a new cluster with multiple tags**

The following ``create-cluster`` example creates a cluster with multiple tags.  For more information about adding tags using shorthand syntax, see `Using Shorthand Syntax with the AWS Command Line Interface <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-shorthand.html>`_ in the *AWS CLI User Guide*. ::

    aws ecs create-cluster \
        --cluster-name MyCluster \
        --tags key=key1,value=value1 key=key2,value=value2 key=key3,value=value3

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
                },
                {
                    "key": "key3",
                    "value": "value3"
                }
            ]
        }
    }

For more information, see `Creating a Cluster <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create_cluster.html>`_ in the *Amazon ECS Developer Guide*.
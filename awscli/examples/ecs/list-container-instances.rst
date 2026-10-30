**To list the container instances in a cluster**

The following ``list-container-instances`` example lists all of the available container instances in a cluster. ::

    aws ecs list-container-instances \
        --cluster MyCluster

Output::

    {
        "containerInstanceArns": [
            "arn:aws:ecs:us-west-2:123456789012:container-instance/MyCluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "arn:aws:ecs:us-west-2:123456789012:container-instance/MyCluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        ]
    }

For more information, see `Amazon EC2 container instances for Amazon ECS <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-capacity.html>`__ in the *Amazon ECS Developer Guide*.

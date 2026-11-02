**To delete one or more custom attributes from an Amazon ECS resource**

The following ``delete-attributes`` example deletes an attribute with the name ``stack`` from a container instance. ::

    aws ecs delete-attributes \
        --attributes name=stack,targetId=arn:aws:ecs:us-west-2:123456789012:container-instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "attributes": [
            {
                "name": "stack",
                "targetId": "arn:aws:ecs:us-west-2:123456789012:container-instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "value": "production"
            }
        ]
    }

For more information, see `Define which container instances Amazon ECS uses for tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-placement-constraints.html>`__ in the *Amazon ECS Developer Guide*.

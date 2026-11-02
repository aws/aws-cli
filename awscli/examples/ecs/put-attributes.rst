**To create an attribute and associate it with an Amazon ECS resource**

The following ``put-attributes`` example applies an attribute with the name stack and the value production to a container instance. ::

    aws ecs put-attributes \
        --attributes name=stack,value=production,targetId=arn:aws:ecs:us-west-2:123456789012:container-instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111
        
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

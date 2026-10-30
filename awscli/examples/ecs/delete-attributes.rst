**To delete one or more custom attributes from an Amazon ECS resource**

The following ``delete-attributes`` example deletes an attribute with the name ``stack`` from a container instance. ::

    aws ecs delete-attributes \
        --attributes name=stack,targetId=arn:aws:ecs:us-west-2:130757420319:container-instance/1c3be8ed-df30-47b4-8f1e-6e68ebd01f34

Output::

    {
        "attributes": [
            {
                "name": "stack",
                "targetId": "arn:aws:ecs:us-west-2:130757420319:container-instance/1c3be8ed-df30-47b4-8f1e-6e68ebd01f34",
                "value": "production"
            }
        ]
    }

For more information, see `Define which container instances Amazon ECS uses for tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-placement-constraints.html>`__ in the *Amazon ECS Developer Guide*.

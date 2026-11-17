**To deregister a scalable target**

The following ``deregister-scalable-target`` example deregisters a scalable target for an Amazon ECS service called `web-app` that is running in the `default` cluster. ::

    aws application-autoscaling deregister-scalable-target \
        --service-namespace ecs \
        --scalable-dimension ecs:service:DesiredCount \
        --resource-id service/default/web-app

This command produces no output.

For more information, see `Application Auto Scaling concepts <https://docs.aws.amazon.com/autoscaling/application/userguide/getting-started.html>`__ in the *Application Auto Scaling User Guide*.

The following ``deregister-scalable-target`` example deregisters a scalable target for a custom resource. The custom-resource-id.txt file contains a string that identifies the Resource ID, which, for a custom resource, is the path to the custom resource through your Amazon API Gateway endpoint. ::

    aws application-autoscaling deregister-scalable-target \
        --service-namespace custom-resource \
        --scalable-dimension custom-resource:ResourceType:Property \
        --resource-id file://~/custom-resource-id.txt

Contents of ``custom-resource-id.txt``::

    https://example.execute-api.us-west-2.amazonaws.com/prod/scalableTargetDimensions/1-23456789

For more information, see `Custom resources and Application Auto Scaling <https://docs.aws.amazon.com/autoscaling/application/userguide/services-that-can-integrate-custom.html>`__ in the *Application Auto Scaling User Guide*.

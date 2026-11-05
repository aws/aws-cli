**To list all service instances**

The following ``list-service-instances`` example lists service instances. ::

    aws proton list-service-instances

Output::

    {
        "serviceInstances": [
            {
                "arn": "arn:aws:proton:region-id:123456789012:service/simple-svc/service-instance/instance-one",
                "createdAt": "2020-11-28T22:40:50.512000+00:00",
                "deploymentStatus": "SUCCEEDED",
                "environmentName": "simple-env",
                "lastDeploymentAttemptedAt": "2020-11-28T22:40:50.512000+00:00",
                "lastDeploymentSucceededAt": "2020-11-28T22:40:50.512000+00:00",
                "name": "instance-one",
                "serviceName": "simple-svc",
                "templateMajorVersion": "1",
                "templateMinorVersion": "0",
                "templateName": "fargate-service"
            }
        ]
    }

For more information, see `View service instance data <https://docs.aws.amazon.com/proton/latest/adminguide/ag-svc-instance-view.html>`__ in the *The AWS Proton Administrator Guide* or `View service instance data <https://docs.aws.amazon.com/proton/latest/userguide/ag-svc-instance-view.html>`__ in the *The AWS Proton User Guide*.

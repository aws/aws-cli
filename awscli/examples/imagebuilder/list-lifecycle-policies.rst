**To list enabled lifecycle policies**

The following ``list-lifecycle-policies`` example lists the lifecycle policies in your account that have ``ENABLED`` status. ::

    aws imagebuilder list-lifecycle-policies \
        --filters name=status,values=ENABLED

Output::

    {
        "lifecyclePolicySummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-ami-policy",
                "name": "my-example-ami-policy",
                "description": "Deletes AMI image builds after they reach 6 months old",
                "status": "ENABLED",
                "executionRole": "arn:aws:iam::123456789012:role/my-example-lifecycle-role",
                "resourceType": "AMI_IMAGE",
                "dateCreated": "2026-09-09T19:36:17.612000+00:00",
                "tags": {}
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-container-policy",
                "name": "my-example-container-policy",
                "description": "Deletes container image builds after they reach 6 months old",
                "status": "ENABLED",
                "executionRole": "arn:aws:iam::123456789012:role/my-example-lifecycle-role",
                "resourceType": "CONTAINER_IMAGE",
                "dateCreated": "2026-09-09T19:36:19.339000+00:00",
                "tags": {}
            }
        ]
    }

For more information, see `List lifecycle management policies for Image Builder image resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/list-lifecycle-policies.html>`__ in the *EC2 Image Builder User Guide*.

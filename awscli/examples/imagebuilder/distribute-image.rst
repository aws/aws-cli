**To distribute an existing AMI**

The following ``distribute-image`` example distributes an AMI that you own to the targets defined in the specified distribution configuration. It returns the ARN of a new Image Builder image resource that you can use with ``get-image`` to monitor distribution progress. ::

    aws imagebuilder distribute-image \
        --source-image ami-1234567890abcdef0 \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution-configuration \
        --execution-role arn:aws:iam::123456789012:role/aws-service-role/imagebuilder.amazonaws.com/AWSServiceRoleForImageBuilder \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-source-ami/1.0.0/1"
    }

For more information, see `Manage Image Builder distribution settings <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-distribution-settings.html>`__ in the *EC2 Image Builder User Guide*.

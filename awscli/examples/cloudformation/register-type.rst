**To register a resource type**

The following ``register-type`` example registers the specified resource type as a private resource type in the user's account. ::

    aws cloudformation register-type \
        --type-name My::Organization::ResourceName \
        --schema-handler-package s3://amzn-s3-demo-bucket_name/my-organization-resource_name.zip \
        --type RESOURCE

Output::

    {
        "RegistrationToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Registering extensions for use in the CloudFormation registry <https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-register.html>`__ in the *CloudFormation Command Line Interface (CLI) User Guide*.

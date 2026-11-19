**Example 1: To create an infrastructure configuration**

The following ``create-infrastructure-configuration`` example creates an infrastructure configuration that gives Image Builder a choice of two instance types for its build and test instances. ::

    aws imagebuilder create-infrastructure-configuration \
        --name my-example-infrastructure \
        --description "An infrastructure configuration for Amazon Linux builds" \
        --instance-profile-name EC2InstanceProfileForImageBuilder \
        --instance-types t3.medium t3.large \
        --terminate-instance-on-failure \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure"
    }

**Example 2: To create an infrastructure configuration with instance placement and metadata options**

The following ``create-infrastructure-configuration`` example creates an infrastructure configuration that places your build and test instances in a single Availability Zone and requires IMDSv2 for instance metadata requests. It also applies resource tags to the resources that Image Builder creates during the build. ::

    aws imagebuilder create-infrastructure-configuration \
        --name my-example-infrastructure \
        --description "An infrastructure configuration that pins build instances to one Availability Zone and requires IMDSv2" \
        --instance-profile-name my-example-instance-role \
        --placement availabilityZone=us-west-2a \
        --instance-metadata-options httpTokens=required,httpPutResponseHopLimit=2 \
        --resource-tags CostCenter=12345,Environment=test \
        --terminate-instance-on-failure \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure"
    }

For more information, see `Create an infrastructure configuration <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-infra-config.html>`__ in the *EC2 Image Builder User Guide*.

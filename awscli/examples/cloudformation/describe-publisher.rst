**To describe a publisher**

The following ``describe-publisher`` example configures the information for a publisher. ::

    aws cloudformation describe-publisher \
        --publisher-id 000q6TfUovXsEMmgKowxDZLlwqr2QUsh

Output::

    {
        "PublisherId": "000q6TfUovXsEMmgKowxDZLlwqr2QUshd2e75c8c",
        "PublisherStatus": "VERIFIED",
        "IdentityProvider": "AWS_Marketplace",
        "PublisherProfile": "https://aws.amazon.com/marketplace/seller-profile?id=a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Using the AWS CloudFormation registry <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html>`__ in the *AWS CloudFormation User Guide*.
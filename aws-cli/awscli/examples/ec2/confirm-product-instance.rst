**To confirm the product instance**

The following ``confirm-product-instance`` example determines whether the specified product code is associated with the specified instance. ::

    aws ec2 confirm-product-instance \
        --product-code 774F4FF8 \
        --instance-id i-1234567890abcdef0

Output::

    {
        "OwnerId": "123456789012"
    }

For more information, see `Paid AMIs in the AWS Marketplace for Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/paid-amis.html>`__ in the *Amazon EC2 User Guide*.

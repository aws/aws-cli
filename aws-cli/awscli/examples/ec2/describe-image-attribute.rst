**Example 1: To describe the launch permissions for an AMI**

The following ``describe-image-attribute`` example describes the launch permissions for the specified AMI. ::

    aws ec2 describe-image-attribute \
        --image-id ami-5731123e \
        --attribute launchPermission

Output::

    {
        "LaunchPermissions": [
            {
                "UserId": "123456789012"
            }
        ],
        "ImageId": "ami-5731123e"
    }

For more information, see `Share an AMI with specific AWS accounts <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharingamis-explicit.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe the product codes for an AMI**

The following ``describe-image-attribute`` example describes the product codes for the specified AMI. Note that this AMI has no product codes. ::

    aws ec2 describe-image-attribute \
        --image-id ami-5731123e \
        --attribute productCodes

Output::

    {
        "ProductCodes": [],
        "ImageId": "ami-5731123e"
    }

For more information, see `Paid AMIs in the AWS Marketplace for Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/paid-amis.html>`__ in the *Amazon EC2 User Guide*.

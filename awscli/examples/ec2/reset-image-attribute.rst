**To reset the launchPermission attribute**

The following ``reset-image-attribute`` example resets the ``launchPermission`` attribute for the specified AMI to its default value. By default, AMIs are private. ::

    aws ec2 reset-image-attribute \
        --image-id ami-5731123e \
        --attribute launchPermission

This command produces no output.

For more information, see `Share an AMI with specific AWS accounts <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharingamis-explicit.html>`__ in the *Amazon EC2 User Guide*.

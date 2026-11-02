**To retrieve a screenshot of a running instance**

The following ``get-console-screenshot`` example retrieves a screenshot of the specified instance in .jpg format. The screenshot is returned as a Base64-encoded string. ::

    aws ec2 get-console-screenshot \
        --instance-id i-1234567890abcdef0

Output::

    {
        "ImageData": "997987/8kgj49ikjhewkwwe0008084EXAMPLE",
        "InstanceId": "i-1234567890abcdef0"
    }

For more information, see `Troubleshoot an unreachable Amazon EC2 instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/troubleshoot-unreachable-instance.html#instance-console-screenshot>`__ in the *Amazon EC2 User Guide*.

**To deregister an AMI**

The following ``deregister-image`` example deregisters the specified AMI. ::

    aws ec2 deregister-image \
        --image-id ami-4fa54026

Output::

    {
        "Return": true
    }

For more information, see `Deregister an Amazon EC2 AMI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/deregister-ami.html>`__ in the *Amazon EC2 User Guide*.

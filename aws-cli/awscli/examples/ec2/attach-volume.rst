**To attach a volume to an instance**

The following ``attach-volume`` example attaches a volume (``vol-1234567890abcdef0``) to an instance (``i-01474ef662b89480``) as ``/dev/sdf``. ::

    aws ec2 attach-volume \
        --volume-id vol-1234567890abcdef0 \
        --instance-id i-01474ef662b89480 \
        --device /dev/sdf

Output::

    {
        "AttachTime": "2024-03-10T21:47:12.000Z",
        "InstanceId": "i-01474ef662b89480",
        "VolumeId": "vol-1234567890abcdef0",
        "State": "attaching",
        "Device": "/dev/sdf"
    }

For more information, see `Attach an Amazon EBS volume to an Amazon EC2 instance <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-attaching-volume.html>`__ in the *Amazon EBS User Guide*.

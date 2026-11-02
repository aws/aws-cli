**To detach a volume from an instance**

The following ``detach-volume`` example detaches the volume (``vol-049df61146c4d7901``) from the instance it is attached to. ::

    aws ec2 detach-volume \
        --volume-id vol-049df61146c4d7901

Output::

    {
        "AttachTime": "2014-02-27T19:23:06.000Z",
        "InstanceId": "i-1234567890abcdef0",
        "VolumeId": "vol-049df61146c4d7901",
        "State": "detaching",
        "Device": "/dev/sdb"
    }

For more information, see `Detach an Amazon EBS volume from an Amazon EC2 instance <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-detaching-volume.html>`__ in the *Amazon EBS User Guide*.

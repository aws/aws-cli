**To describe a volume attribute**

The following ``describe-volume-attribute`` example describes the ``autoEnableIo`` attribute of the volume with the ID ``vol-049df61146c4d7901``. ::

    aws ec2 describe-volume-attribute \
        --volume-id vol-049df61146c4d7901 \
        --attribute autoEnableIO

Output::

    {
        "AutoEnableIO": {
            "Value": false
        },
        "VolumeId": "vol-049df61146c4d7901"
    }

For more information, see `Amazon EBS volume status checks <https://docs.aws.amazon.com/ebs/latest/userguide/monitoring-volume-checks.html>`__ in the *Amazon EBS User Guide*.

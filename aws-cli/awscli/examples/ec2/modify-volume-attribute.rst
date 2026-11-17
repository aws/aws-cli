**To modify a volume attribute**

The following ``modify-volume-attribute`` example sets the ``autoEnableIo`` attribute of the volume with the ID ``vol-1234567890abcdef0`` to ``true``. ::

    aws ec2 modify-volume-attribute \
        --volume-id vol-1234567890abcdef0 \
        --auto-enable-io

This command produces no output.

For more information, see `Amazon EBS volume status checks <https://docs.aws.amazon.com/ebs/latest/userguide/monitoring-volume-checks.html>`__ in the *Amazon EBS User Guide*.

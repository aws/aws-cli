**To enable I/O for a volume**

The following ``enable-volume-io`` example enables I/O on volume ``vol-1234567890abcdef0``. ::

    aws ec2 enable-volume-io \
        --volume-id vol-1234567890abcdef0

This command produces no output.

For more information, see `Work with an impaired Amazon EBS volume <https://docs.aws.amazon.com/ebs/latest/userguide/work_volumes_impaired.html>`__ in the *Amazon EBS User Guide*.

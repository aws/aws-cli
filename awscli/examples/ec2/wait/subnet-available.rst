**To wait until a subnet is available**

The following ``wait subnet-available`` example pauses and resumes running only after it confirms that the specified subnet is available. ::

    aws ec2 wait subnet-available \
        --subnet-ids subnet-1234567890abcdef0

This command produces no output.

For more information, see `Subnets for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html>`__ in the *Amazon VPC User Guide*.

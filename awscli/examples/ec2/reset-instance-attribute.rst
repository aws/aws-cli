**Example 1: To reset the sourceDestCheck attribute**

The following ``reset-instance-attribute`` example resets the ``sourceDestCheck`` attribute of the specified instance. The instance must be in a VPC. ::

    aws ec2 reset-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute sourceDestCheck

This command produces no output.

For more information, see `NAT instances <https://docs.aws.amazon.com/vpc/latest/userguide/VPC_NAT_Instance.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To reset the kernel attribute**

The following ``reset-instance-attribute`` example resets the ``kernel`` attribute of the specified instance. The instance must be in the ``stopped`` state. ::

    aws ec2 reset-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute kernel

This command produces no output.

For more information, see `User provided kernels <https://docs.aws.amazon.com/linux/al2/ug/UserProvidedKernels.html>`__ in the *Amazon Linux 2 User Guide*.

**Example 3: To reset the ramdisk attribute**

The following ``reset-instance-attribute`` example resets the ``ramdisk`` attribute of the specified instance. The instance must be in the ``stopped`` state. ::

    aws ec2 reset-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute ramdisk

This command produces no output.

For more information, see `User provided kernels <https://docs.aws.amazon.com/linux/al2/ug/UserProvidedKernels.html>`__ in the *Amazon Linux 2 User Guide*.

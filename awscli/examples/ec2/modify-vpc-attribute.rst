**Example 1: To modify the enableDnsSupport attribute**

The following ``modify-vpc-attribute`` example modifies the ``enableDnsSupport`` attribute. This attribute indicates whether DNS resolution is enabled for the VPC. If this attribute is ``true``, the Amazon DNS server resolves DNS hostnames for your instances to their corresponding IP addresses; otherwise, it does not. ::

    aws ec2 modify-vpc-attribute \
        --vpc-id vpc-a01106c2 \
        --enable-dns-support "{\"Value\":false}"

This command produces no output.

For more information, see `View and update DNS attributes for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns-updating.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To modify the enableDnsHostnames attribute**

The following ``modify-vpc-attribute`` example modifies the ``enableDnsHostnames`` attribute. This attribute indicates whether instances launched in the VPC get DNS hostnames. If this attribute is ``true``, instances in the VPC get DNS hostnames; otherwise, they do not. ::

    aws ec2 modify-vpc-attribute \
        --vpc-id vpc-a01106c2 \
        --enable-dns-hostnames "{\"Value\":false}"

This command produces no output.

For more information, see `View and update DNS attributes for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns-updating.html>`__ in the *Amazon VPC User Guide*.

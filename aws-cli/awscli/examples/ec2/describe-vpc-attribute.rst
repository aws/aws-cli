**Example 1: To describe the enableDnsSupport attribute**

The following ``describe-vpc-attribute`` example describes the ``enableDnsSupport`` attribute. This attribute indicates whether DNS resolution is enabled for the VPC. If this attribute is ``true``, the Amazon DNS server resolves DNS hostnames for your instances to their corresponding IP addresses; otherwise, it does not. ::

    aws ec2 describe-vpc-attribute \
        --vpc-id vpc-a01106c2 \
        --attribute enableDnsSupport

Output::

    {
        "VpcId": "vpc-a01106c2",
        "EnableDnsSupport": {
            "Value": true
        }
    }

For more information, see `DNS attributes for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To describe the enableDnsHostnames attribute**

The following ``describe-vpc-attribute`` example describes the ``enableDnsHostnames`` attribute. This attribute indicates whether the instances launched in the VPC get DNS hostnames. If this attribute is ``true``, instances in the VPC get DNS hostnames; otherwise, they do not. ::

    aws ec2 describe-vpc-attribute \
        --vpc-id vpc-a01106c2 \
        --attribute enableDnsHostnames

Output::

    {
        "VpcId": "vpc-a01106c2",
        "EnableDnsHostnames": {
            "Value": true
        }
    }

For more information, see `DNS attributes for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html>`__ in the *Amazon VPC User Guide*.

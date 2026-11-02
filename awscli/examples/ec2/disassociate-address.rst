**Example 1: To disassociate an Elastic IP address in EC2-Classic**

The following ``disassociate-address`` example disassociates an Elastic IP address from an instance in EC2-Classic. ::

    aws ec2 disassociate-address \
        --public-ip 198.51.100.0

This command produces no output.

For more information, see `Elastic IP addresses <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To disassociate an Elastic IP address in EC2-VPC**

The following ``disassociate-address`` example disassociates an Elastic IP address from an instance in a VPC. ::

    aws ec2 disassociate-address \
        --association-id eipassoc-2bebb745

This command produces no output.

For more information, see `Elastic IP addresses <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html>`__ in the *Amazon EC2 User Guide*.

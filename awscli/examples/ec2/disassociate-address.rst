**Example 1: To disassociate an Elastic IP address in EC2-Classic**

The following ``disassociate-address`` example disassociates an Elastic IP address from an instance in EC2-Classic. This command produces no output. ::

    aws ec2 disassociate-address \
        --public-ip 198.51.100.0

**Example 2: To disassociate an Elastic IP address in EC2-VPC**

The following ``disassociate-address`` example disassociates an Elastic IP address from an instance in a VPC. This command produces no output. ::

    aws ec2 disassociate-address \
        --association-id eipassoc-2bebb745

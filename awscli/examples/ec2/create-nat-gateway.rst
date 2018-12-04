**To create a NAT gateway**

This example creates a NAT gateway in subnet ``subnet-1a2b3c4d`` and associates an Elastic IP address with the allocation ID ``eipalloc-37fc1a52`` with the NAT gateway. 

Command::

  aws ec2 create-nat-gateway --subnet-id subnet-1a2b3c4d --allocation-id eipalloc-37fc1a52

Output::

  {
    "NatGateway": {
      "NatGatewayAddresses": [
        {
          "AllocationId": "eipalloc-37fc1a52"
        }
      ], 
      "VpcId": "vpc-1122aabb", 
      "State": "pending", 
      "NatGatewayId": "nat-08d48af2a8e83edfd", 
      "SubnetId": "subnet-1a2b3c4d", 
      "CreateTime": "2015-12-17T12:45:26.732Z"
    }
  }
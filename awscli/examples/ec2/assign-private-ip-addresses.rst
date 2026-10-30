**Example 1: To assign a specific secondary private IP address to a network interface**

The following ``assign-private-ip-addresses`` example assigns the specified secondary private IP address to the specified network interface. If the command succeeds, no output is returned. ::

    aws ec2 assign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --private-ip-addresses 10.0.0.82

**Example 2: To assign secondary private IP addresses that Amazon EC2 selects to a network interface**

The following ``assign-private-ip-addresses`` example assigns two secondary private IP addresses to the specified network interface. Amazon EC2 automatically assigns these IP addresses from the available IP addresses in the CIDR block range of the subnet the network interface is associated with. If the command succeeds, no output is returned. ::

    aws ec2 assign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --secondary-private-ip-address-count 2

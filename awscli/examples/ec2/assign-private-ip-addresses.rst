**Example 1: To assign a specific secondary private IP address to a network interface**

The following ``assign-private-ip-addresses`` example assigns the specified secondary private IP address to the specified network interface. ::

    aws ec2 assign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --private-ip-addresses 10.0.0.82

Output::

    {
        "NetworkInterfaceId": "eni-e5aa89a3",
        "AssignedPrivateIpAddresses": [
            {
                "PrivateIpAddress": "10.0.0.82"
            }
        ]
    }

For more information, see `Secondary IP addresses for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-secondary-ip-addresses.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To assign secondary private IP addresses that Amazon EC2 selects to a network interface**

The following ``assign-private-ip-addresses`` example assigns two secondary private IP addresses to the specified network interface. Amazon EC2 automatically assigns these IP addresses from the available IP addresses in the CIDR block range of the subnet the network interface is associated with. ::

    aws ec2 assign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --secondary-private-ip-address-count 2

Output::

    {
        "NetworkInterfaceId": "eni-e5aa89a3",
        "AssignedPrivateIpAddresses": [
            {
                "PrivateIpAddress": "10.0.0.93"
            },
            {
                "PrivateIpAddress": "10.0.0.147"
            }
        ]
    }

For more information, see `Secondary IP addresses for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-secondary-ip-addresses.html>`__ in the *Amazon EC2 User Guide*.

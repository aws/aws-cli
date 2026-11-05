**To view the attributes of the domain name associated with an elastic IP address**

The following ``describe-addresses-attribute`` example returns the attributes of the domain name associated with the elastic IP address.

The following command is for Linux. ::

    aws ec2 describe-addresses-attribute \
        --allocation-ids eipalloc-abcdef01234567890 \
        --attribute domain-name
        
The following command is for Windows. ::

    aws ec2 describe-addresses-attribute ^
        --allocation-ids eipalloc-abcdef01234567890 ^
        --attribute domain-name
        
Output::

    {
        "Addresses": [
            {
                "PublicIp": "192.0.2.0",
                "AllocationId": "eipalloc-abcdef01234567890",
                "PtrRecord": "example.com."
            }
        ]
    }

To view the attributes of an elastic IP address, you must have first associated a domain name with the elastic IP address. For more information, see `Create a reverse DNS record for email on Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Elastic_Addressing_Reverse_DNS.html>`__ in the *Amazon EC2 User Guide*. To associate a domain name with an elastic IP address, see `modify-address-attribute <https://docs.aws.amazon.com/cli/latest/reference/ec2/modify-address-attribute.html>`__ in the *AWS CLI Command Reference*.

**Example 1: To authorize access to an EC2 security group**

The following ``authorize-cluster-security-group-ingress`` example authorizes access to a named Amazon EC2 security group. ::

    aws redshift authorize-cluster-security-group-ingress \
        --cluster-security-group-name mysecuritygroup \
        --ec2-security-group-name myec2securitygroup \
        --ec2-security-group-owner-id 123456789012

Output::

    {
        "ClusterSecurityGroup": {
            "ClusterSecurityGroupName": "mysecuritygroup",
            "Description": "This is my cluster security group",
            "EC2SecurityGroups": [
                {
                    "Status": "authorizing",
                    "EC2SecurityGroupName": "myec2securitygroup",
                    "EC2SecurityGroupOwnerId": "123456789012",
                    "Tags": []
                }
            ],
            "IPRanges": [],
            "Tags": []
        }
    }

For more information, see `Infrastructure security in Amazon Redshift <https://docs.aws.amazon.com/redshift/latest/mgmt/security-network-isolation.html>`__ in the *Amazon Redshift Management Guide*.

**Example 2: To authorize access to a CIDR range**

The following ``authorize-cluster-security-group-ingress`` example authorizes access to a CIDR range. ::

    aws redshift authorize-cluster-security-group-ingress \
        --cluster-security-group-name mysecuritygroup \
        --cidrip 192.168.100.100/32

Output::

    {
        "ClusterSecurityGroup": {
            "ClusterSecurityGroupName": "mysecuritygroup",
            "Description": "This is my cluster security group",
            "EC2SecurityGroups": [],
            "IPRanges": [
                {
                    "Status": "authorizing",
                    "CIDRIP": "192.168.100.100/32",
                    "Tags": []
                }
            ],
            "Tags": []
        }
    }

For more information, see `Infrastructure security in Amazon Redshift <https://docs.aws.amazon.com/redshift/latest/mgmt/security-network-isolation.html>`__ in the *Amazon Redshift Management Guide*.

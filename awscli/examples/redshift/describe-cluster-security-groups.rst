**To get a description of all cluster security groups**

The following ``describe-cluster-security-groups`` example returns a description of all cluster security groups for the account.
By default, the output is in JSON format. ::

    aws redshift describe-cluster-security-groups

Output::

    {
        "ClusterSecurityGroups": [
            {
                "Description": "default",
                "ClusterSecurityGroupName": "default",
                "EC2SecurityGroups": [],
                "IPRanges": [
                    {
                        "Status": "authorized",
                        "CIDRIP": "0.0.0.0/0"
                    }
                ]
            },
            {
                "Description": "This is my cluster security group",
                "ClusterSecurityGroupName": "mysecuritygroup",
                "EC2SecurityGroups": [],
                "IPRanges": []
            }
        ]
    }

For more information, see `Infrastructure security in Amazon Redshift <https://docs.aws.amazon.com/redshift/latest/mgmt/security-network-isolation.html>`__ in the *Amazon Redshift Management Guide*.

**To create a cluster security group**

The following ``create-cluster-security-group`` example creates a new cluster security group. By default, the output is in JSON format. ::

    aws redshift create-cluster-security-group \
        --cluster-security-group-name mysecuritygroup \
        --description "This is my cluster security group"

Output::

    {
        "ClusterSecurityGroup": {
            "ClusterSecurityGroupName": "mysecuritygroup",
            "Description": "This is my cluster security group",
            "EC2SecurityGroups": [],
            "IPRanges": [],
            "Tags": []
        }
    }

You can also obtain the same information in text format using the ``--output text`` option. ::

    aws redshift create-cluster-security-group \
        --cluster-security-group-name mysecuritygroup \
        --description "This is my cluster security group" \
        --output text

Output::

    This is my cluster security group   123456789012    mysecuritygroup

For more information, see `Infrastructure security in Amazon Redshift <https://docs.aws.amazon.com/redshift/latest/mgmt/security-network-isolation.html>`__ in the *Amazon Redshift Management Guide*.

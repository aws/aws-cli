**To authorize cache security group for ingress**

The following ``authorize-cache-security-group-ingress`` example allows network ingress to a cache security group. ::

    aws elasticache authorize-cache-security-group-ingress \
        --cache-security-group-name "my-sec-grp" \
        --ec2-security-group-name "my-ec2-sec-grp" \
        --ec2-security-group-owner-id "1234567890"

Output::

    {
        "CacheSecurityGroup": {
            "OwnerId": "123456789012",
            "CacheSecurityGroupName": "my-sec-grp",
            "Description": "My cache security group",
            "EC2SecurityGroups": [
                {
                    "Status": "authorizing",
                    "EC2SecurityGroupName": "my-ec2-sec-grp",
                    "EC2SecurityGroupOwnerId": "1234567890"
                }
            ],
            "ARN": "arn:aws:elasticache:us-west-2:123456789012:securitygroup:my-sec-grp"
        }
    }

For more information, see `Self-Service Updates in Amazon ElastiCache <https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Self-Service-Updates.html>`__ in the *Elasticache User Guide*.
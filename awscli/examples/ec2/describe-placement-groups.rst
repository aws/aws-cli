**To describe your placement groups**

The following ``describe-placement-groups`` example describes all of your placement groups. ::

    aws ec2 describe-placement-groups

Output::

    {
        "PlacementGroups": [
            {
                "GroupName": "my-cluster",
                "State": "available",
                "Strategy": "cluster"
            }
        ]
    }

For more information, see `Placement groups for your Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html>`__ in the *Amazon EC2 User Guide*.

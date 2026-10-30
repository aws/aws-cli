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
            },
            ...
        ]
    }

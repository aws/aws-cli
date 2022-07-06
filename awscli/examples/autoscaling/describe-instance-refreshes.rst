**To list instance refreshes**

The following ``describe-instance-refreshes`` example returns a description of all instance refresh requests for the specified Auto Scaling group, including the status message and (if available) the status reason. ::

    aws autoscaling describe-instance-refreshes \
        --auto-scaling-group-name my-asg 

Output::

    {
        "InstanceRefreshes": [
            {
                "InstanceRefreshId": "08b91cf7-8fa6-48af-b6a6-d227f40f1b9b",
                "AutoScalingGroupName": "my-asg",
                "Status": "InProgress",
                "StartTime": "2020-06-02T18:11:27Z",
                "PercentageComplete": 0,
                "InstancesToUpdate": 5
            },
            {
                "InstanceRefreshId": "dd7728d0-5bc4-4575-96a3-1b2c52bf8bb1",
                "AutoScalingGroupName": "my-asg",
                "Status": "Successful",
                "StartTime": "2020-06-02T16:43:19Z",
                "EndTime": "2020-06-02T16:53:37Z",
                "PercentageComplete": 100,
                "InstancesToUpdate": 0
            }
        ]
    }

For more information, see `Replacing Auto Scaling instances based on an instance refresh <https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
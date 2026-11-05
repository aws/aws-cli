**To detach an instance from an Auto Scaling group**

The following ``detach-instances`` example detaches the specified instance from the specified Auto Scaling group. ::

    aws autoscaling detach-instances \
        --instance-ids i-030017cfa84b20135 \
        --auto-scaling-group-name my-asg \
        --should-decrement-desired-capacity

Output::

    {
        "Activities": [
            {
                "ActivityId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AutoScalingGroupName": "my-asg",
                "Description": "Detaching EC2 instance: i-030017cfa84b20135",
                "Cause": "At 2020-10-31T17:35:04Z instance i-030017cfa84b20135 was detached in response to a user request, shrinking the capacity from 2 to 1.",
                "StartTime": "2020-04-12T15:02:16.179Z",
                "StatusCode": "InProgress",
                "Progress": 50,
                "Details": "{\"Subnet ID\":\"subnet-6194ea3b\",\"Availability Zone\":\"us-west-2c\"}"
            }
        ]
    }

For more information, see `Detach or attach instances from your Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-detach-attach-instances.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 1: To describe all tags**

The following ``describe-tags`` example describes all your tags. ::

    aws autoscaling describe-tags

Output::

    {
        "Tags": [
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-asg",
                "PropagateAtLaunch": true,
                "Value": "Research",
                "Key": "Dept"
            },
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-asg",
                "PropagateAtLaunch": true,
                "Value": "WebServer",
                "Key": "Role"
            }
        ]
    }

For more information, see `Tagging Auto Scaling groups and instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 2: To describe tags for a specified group**

The following ``describe-tags`` example uses the ``--filters`` option to describe tags for a specific Auto Scaling group. ::

    aws autoscaling describe-tags \
        --filters Name=auto-scaling-group,Values=my-asg

Output::

    {
        "Tags": [
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-asg",
                "PropagateAtLaunch": true,
                "Value": "Research",
                "Key": "Dept"
            },
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-asg",
                "PropagateAtLaunch": true,
                "Value": "WebServer",
                "Key": "Role"
            }
        ]
    }

For more information, see `Tagging Auto Scaling groups and instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 3: To describe the specified number of tags**

The following ``describe-tags`` example uses the ``--max-items`` option to return a specific number of tags. ::

    aws autoscaling describe-tags \
        --max-items 1

Output::

    {
        "Tags": [
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-asg",
                "PropagateAtLaunch": true,
                "Value": "Research",
                "Key": "Dept"
            }
        ],
        "NextToken": "Z3M3LMPEXAMPLE"
    }

If the output includes a ``NextToken`` field, there are more tags. To get the additional tags, use the value of this field with the ``--starting-token`` option in a subsequent call as follows. ::

    aws autoscaling describe-tags \
        --filters Name=auto-scaling-group,Values=my-asg \
        --starting-token Z3M3LMPEXAMPLE

For more information, see `Tagging Auto Scaling groups and instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
**To describe tags**

This example describes all your tags::

    aws autoscaling describe-tags

The following is example output::

    {
        "Tags": [
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-auto-scaling-group",
                "PropagateAtLaunch": true,
                "Value": "Research",
                "Key": "Dept"
            },
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-auto-scaling-group",
                "PropagateAtLaunch": true,
                "Value": "WebServer",
                "Key": "Role"
            }
        ]
    }

To describe tags for a specific Auto Scaling group, use the ``filters`` parameter::

    aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=my-auto-scaling-group

To return a specific number of tags, use the ``max-items`` parameter::

    aws autoscaling describe-tags --max-items 1

The following is example output::

    {
        "NextToken": "Z3M3LMPEXAMPLE",
        "Tags": [
            {
                "ResourceType": "auto-scaling-group",
                "ResourceId": "my-auto-scaling-group",
                "PropagateAtLaunch": true,
                "Value": "Research",
                "Key": "Dept"
            }
        ]
    }

Use the ``NextToken`` field with the ``starting-token`` parameter in a subsequent call to get the additional tags::

    aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=my-auto-scaling-group --starting-token Z3M3LMPEXAMPLE

For more information, see `Tagging Auto Scaling Groups and Instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Tagging Auto Scaling Groups and Instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html

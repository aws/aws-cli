**To describe tags**

This example describes all your tags. ::

    aws autoscaling describe-tags

The following is example output::

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

To describe tags for a specific Auto Scaling group, use the ``filters`` parameter. ::

    aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=my-asg

To return a specific number of tags, use the ``max-items`` parameter. ::

    aws autoscaling describe-tags --max-items 1

If the output includes a ``NextToken`` field, there are more tags. To get the additional tags, use the value of this field with the ``starting-token`` parameter in a subsequent call as follows. ::

Use the ``NextToken`` field with the ``starting-token`` parameter in a subsequent call to get the additional tags. ::

    aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=my-asg --starting-token Z3M3LMPEXAMPLE

For more information, see `Tagging Auto Scaling groups and instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Tagging Auto Scaling groups and instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html

**To describe tags**

The following ``describe-tags`` command returns all tags::

	aws autoscaling describe-tags

The output of this command is a JSON block that describes the tags for all Auto Scaling groups, similar to the following::

	{
		"Tags": [
			{
				"ResourceType": "auto-scaling-group",
				"ResourceId": "tags-auto-scaling-group",
				"PropagateAtLaunch": true,
				"Value": "Research",
				"Key": "Dept"
			},
			{
				"ResourceType": "auto-scaling-group",
				"ResourceId": "tags-auto-scaling-group",
				"PropagateAtLaunch": true,
				"Value": "WebServer",
				"Key": "Role"
			}
		]
	}

The following example uses the ``filters`` parameter to return tags for a specific Auto Scaling group::

	aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=tags-auto-scaling-group

To return a specific number of tags with this command, use the ``max-items`` parameter::

	aws autoscaling describe-tags --max-items 1

In this example, the output of this command is a JSON block that describes the first tag::

	{
		"NextToken": "None___1",
		"Tags": [
			{
				"ResourceType": "auto-scaling-group",
				"ResourceId": "tags-auto-scaling-group",
				"PropagateAtLaunch": true,
				"Value": "Research",
				"Key": "Dept"
			}
		]
	}

This JSON block includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional tags::

    aws autoscaling describe-tags --filters Name=auto-scaling-group,Values=tags-auto-scaling-group --starting-token None___1

For more information, see `Add, Modify, or Remove Auto Scaling Group Tags`_ in the *Auto Scaling Developer Guide*.

.. _`Add, Modify, or Remove Auto Scaling Group Tags`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASTagging.html


**To create or update tags for an Auto Scaling group**

The following ``create-or-update-tags`` command attaches two tags to an Auto Scaling group::

	aws autoscaling create-or-update-tags --tags ResourceId=tags-auto-scaling-group,ResourceType=auto-scaling-group,Key=Role,Value=WebServer,PropagateAtLaunch=true ResourceId=tags-auto-scaling-group,ResourceType=auto-scaling-group,Key=Dept,Value=Research,PropagateAtLaunch=true

For more information, see `Add, Modify, or Remove Auto Scaling Group Tags`_ in the *Auto Scaling Developer Guide*.

.. _`Add, Modify, or Remove Auto Scaling Group Tags`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASTagging.html


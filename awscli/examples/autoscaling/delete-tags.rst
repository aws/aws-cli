**To delete a tag from an Auto Scaling group**

The following ``delete-tags`` command deletes a tag from an Auto Scaling group::

	aws autoscaling delete-tags --tags ResourceId=tags-auto-scaling-group,ResourceType=auto-scaling-group,Key=Dept,Value=Research

For more information, see `Add, Modify, or Remove Auto Scaling Group Tags`_ in the *Auto Scaling Developer Guide*.

.. _`Add, Modify, or Remove Auto Scaling Group Tags`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASTagging.html


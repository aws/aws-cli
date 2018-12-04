**To delete a tag from an Auto Scaling group**

This example deletes the specified tag from the specified Auto Scaling group::

    aws autoscaling delete-tags --tags ResourceId=my-auto-scaling-group,ResourceType=auto-scaling-group,Key=Dept,Value=Research

For more information, see `Tagging Auto Scaling Groups and Instances`_ in the *Auto Scaling Developer Guide*.

.. _`Tagging Auto Scaling Groups and Instances`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASTagging.html

**To delete a tag from an Auto Scaling group**

This example deletes the specified tag from the specified Auto Scaling group::

    aws autoscaling delete-tags --tags ResourceId=my-auto-scaling-group,ResourceType=auto-scaling-group,Key=Dept,Value=Research

For more information, see `Tagging Auto Scaling Groups and Instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Tagging Auto Scaling Groups and Instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html

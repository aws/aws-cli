**To delete a tag from an Auto Scaling group**

This example deletes the specified tag from the specified Auto Scaling group. ::

    aws autoscaling delete-tags --tags ResourceId=my-asg,ResourceType=auto-scaling-group,Key=Dept,Value=Research

This command returns to the prompt if successful.

For more information, see `Tagging Auto Scaling groups and instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Tagging Auto Scaling groups and instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-tagging.html

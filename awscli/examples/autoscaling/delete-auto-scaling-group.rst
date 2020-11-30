**To delete an Auto Scaling group**

This example deletes the specified Auto Scaling group. ::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name my-asg

This command returns to the prompt if successful.

To delete the Auto Scaling group without waiting for the instances in the group to terminate, use the ``--force-delete`` option. ::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name my-asg --force-delete

This command returns to the prompt if successful.

For more information, see `Deleting your Auto Scaling infrastructure`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Deleting your Auto Scaling infrastructure`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-process-shutdown.html

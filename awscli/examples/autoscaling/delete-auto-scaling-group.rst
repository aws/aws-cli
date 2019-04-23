**To delete an Auto Scaling group**

This example deletes the specified Auto Scaling group::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group

To delete the Auto Scaling group without waiting for the instances in the group to terminate, use the ``--force-delete`` parameter::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name my-auto-scaling-group --force-delete

For more information, see `Deleting Your Auto Scaling Infrastructure`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Deleting Your Auto Scaling Infrastructure`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-process-shutdown.html

**To delete an Auto Scaling group**

The following ``delete-auto-scaling-group`` command deletes an Auto Scaling group::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name delete-me-auto-scaling-group

If you want to delete the Auto Scaling group without waiting for the instances in the group to terminate, use the ``--force-delete`` parameter::

    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name delete-me-auto-scaling-group --force-delete

For more information, see `Shut Down Your Auto Scaling Process`_ in the *Auto Scaling Developer Guide*.

.. _`Shut Down Your Auto Scaling Process`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-process-shutdown.html


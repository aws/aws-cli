**To execute an Auto Scaling policy**

This example executes the specified Auto Scaling policy for the specified Auto Scaling group::

    aws autoscaling execute-policy --auto-scaling-group-name my-auto-scaling-group --policy-name ScaleIn --honor-cooldown

For more information, see `Dynamic Scaling`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Dynamic Scaling`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html

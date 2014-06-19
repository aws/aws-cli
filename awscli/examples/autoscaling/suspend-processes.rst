**To suspend Auto Scaling processes**

The following ``suspend-processes`` command suspends a scaling process for an Auto Scaling group::

	aws autoscaling suspend-processes --auto-scaling-group-name basic-auto-scaling-group --scaling-processes AlarmNotification

For more information, see `Suspend and Resume Auto Scaling Process`_ in the *Auto Scaling Developer Guide*.

.. _`Suspend and Resume Auto Scaling Process`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_SuspendResume.html


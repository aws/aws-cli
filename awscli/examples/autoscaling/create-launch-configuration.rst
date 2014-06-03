**To create a launch configuration**

The following example uses the ``create-launch-configuration`` command to create a launch configuration::

     aws autoscaling create-launch-configuration --launch-configuration-name my-test-lc --image-id ami-c6169af6 --instance-type m1.medium

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html

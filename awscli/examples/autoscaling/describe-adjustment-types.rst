**To describe the Auto Scaling adjustment types**

This example describes the adjustment types available for your Auto Scaling groups::

	aws autoscaling describe-adjustment-types

The following is example output::

  {
    "AdjustmentTypes": [
      {
        "AdjustmentType": "ChangeInCapacity"
      }
      {
        "AdjustmentType": "ExactCapcity"
      }
      {
        "AdjustmentType": "PercentChangeInCapacity"
      }
    ]
  }

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html


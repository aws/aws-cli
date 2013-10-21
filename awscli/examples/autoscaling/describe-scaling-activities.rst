**To get description of the scaling activities in an Auto Scaling group**

The following ``describe-scaling-activities`` command describes the scaling activities for the specified Auto Scaling group::

    aws autoscaling describe-scaling-activities --auto-scaling-group-name my-test-asg

The output of this command is a JSON block that describes the scaling activities for the specified Auto Scaling group, similar to the following::

      {
          "Activities": [
              {
                  "Description": "Launching a new EC2 instance: i-4ba0837f",
                  "AutoScalingGroupName": "my-test-asg",
                  "ActivityId": "f9f2d65b-f1f2-43e7-b46d-d86756459699",
                  "Details": "{"Availability Zone":"us-west-2c"}",
                  "StartTime": "2013-08-19T20:53:29.930Z",
                  "Progress": 100,
                  "EndTime": "2013-08-19T20:54:02Z",
                  "Cause": "At 2013-08-19T20:53:25Z a user request created an AutoScalingGroup changing the desired capacity from 0 to 1.  At 2013-08-19T20:53:29Z an instance was started in response to a difference between desired and actual capa city, increasing the capacity from 0 to 1.",
                  "StatusCode": "Successful"
              }
         ]
      }

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html


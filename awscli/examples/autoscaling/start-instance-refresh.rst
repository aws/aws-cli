**Example 1: To start an instance refresh with command line parameters**

The following ``start-instance-refresh`` example starts an instance refresh using command line arguments. The optional ``preferences`` parameter specifies an ``InstanceWarmup`` of ``400`` seconds and a ``MinHealthyPercentage`` of ``50`` percent. ::

    aws autoscaling start-instance-refresh \
        --auto-scaling-group-name my-asg \
        --preferences '{"InstanceWarmup": 400, "MinHealthyPercentage": 50}'

Output::

    {
        "InstanceRefreshId": "08b91cf7-8fa6-48af-b6a6-d227f40f1b9b"
    }

For more information, see `Replacing Auto Scaling Instances Based on an Instance Refresh <https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 2: To start an instance refresh using a JSON file**

The following ``start-instance-refresh`` example starts an instance refresh using a JSON file. You can specify the Auto Scaling group and define your preferences in a JSON file, as shown in the following example. ::

    aws autoscaling start-instance-refresh \
        --cli-input-json file://config.json

Contents of ``config.json``::

    {
        "AutoScalingGroupName": "my-asg",
        "Preferences": {
            "InstanceWarmup": 400,
            "MinHealthyPercentage": 50
        }
    }

Output::

    {
        "InstanceRefreshId": "08b91cf7-8fa6-48af-b6a6-d227f40f1b9b"
    }

For more information, see `Replacing Auto Scaling Instances Based on an Instance Refresh <https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**To describe your Reserved Instances**

This example command describes the Reserved Instances that you own.

Command::

  aws ec2 describe-reserved-instances

Output::

  {
    "ReservedInstances": [
        {
            "ReservedInstancesId": "b847fa93-e282-4f55-b59a-1342fexample",
            "OfferingType": "Medium Utilization",
            "AvailabilityZone": "us-west-1a",
            "End": "2016-08-14T21:34:34.000Z",
            "ProductDescription": "Linux/UNIX",
            "UsagePrice": 0.01,
            "RecurringCharges": [],
            "Start": "2013-08-15T21:34:35.086Z",
            "State": "active",
            "FixedPrice": 82.0,
            "CurrencyCode": "USD",
            "Duration": 94608000,
            "InstanceTenancy": "default",
            "InstanceType": "t1.micro",
            "InstanceCount": 10
        },
        ...
    ]
  }

**To describe your Reserved Instances using filters**

This example filters the response to include only one-year, t1.micro Linux/UNIX Reserved Instances in us-west-1c.

Command::

  aws ec2 describe-reserved-instances --filters Name=duration,Values=31536000, Name=instance-type,Values=t1.micro, Name=product-description,Values=Linux/UNIX, Name=availability-zone,Values=us-west-1c

Output::

  {
      "ReservedInstances": [
          {
              "ReservedInstancesId": "f127bd27-edb7-44c9-a0eb-0d7e09259af0",
              "OfferingType": "Medium Utilization",
              "AvailabilityZone": "us-west-1c",
              "End": "2014-08-15T21:34:34.000Z",
              "ProductDescription": "Linux/UNIX",
              "UsagePrice": 0.01,
              "RecurringCharges": [],
              "Start": "2013-08-15T21:34:35.848Z",
              "State": "active",
              "FixedPrice": 54.0,
              "CurrencyCode": "USD",
              "Duration": 31536000,
              "InstanceTenancy": "default",
              "InstanceType": "t1.micro",
              "InstanceCount": 5
          }
      ]
  }

For more information, see `Using Amazon EC2 Instances`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Amazon EC2 Instances`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html


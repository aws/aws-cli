**Example 1: To describe your Reserved Instances**

The following ``describe-reserved-instances`` example describes the Reserved Instances that you own. ::

    aws ec2 describe-reserved-instances

Output::

    {
        "ReservedInstances": [
            {
                "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "OfferingType": "No Upfront",
                "AvailabilityZone": "us-west-2c",
                "End": "2016-08-14T21:34:34.000Z",
                "ProductDescription": "Linux/UNIX",
                "UsagePrice": 0.00,
                "RecurringCharges": [
                    {
                        "Amount": 0.104,
                        "Frequency": "Hourly"
                    }
                ],
                "Start": "2015-08-15T21:34:35.086Z",
                "State": "active",
                "FixedPrice": 0.0,
                "CurrencyCode": "USD",
                "Duration": 31536000,
                "InstanceTenancy": "default",
                "InstanceType": "m3.medium",
                "InstanceCount": 2
            }
        ]
    }

For more information, see `Reserved Instances for Amazon EC2 overview <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe your Reserved Instances using filters**

The following ``describe-reserved-instances`` example filters the response to include only three-year, t2.micro Linux/UNIX Reserved Instances in us-west-2c. ::

    aws ec2 describe-reserved-instances \
        --filters Name=duration,Values=94608000 Name=instance-type,Values=t2.micro Name=product-description,Values=Linux/UNIX Name=availability-zone,Values=us-west-2c

Output::

    {
        "ReservedInstances": [
            {
                "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "OfferingType": "All Upfront",
                "AvailabilityZone": "us-west-2c",
                "End": "2018-03-26T21:34:34.000Z",
                "ProductDescription": "Linux/UNIX",
                "UsagePrice": 0.00,
                "RecurringCharges": [],
                "Start": "2015-03-27T21:34:35.848Z",
                "State": "active",
                "FixedPrice": 151.0,
                "CurrencyCode": "USD",
                "Duration": 94608000,
                "InstanceTenancy": "default",
                "InstanceType": "t2.micro",
                "InstanceCount": 1
            }
        ]
    }

For more information, see `Reserved Instances for Amazon EC2 overview <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html>`__ in the *Amazon EC2 User Guide*.

**Example 1: To describe Reserved Instances offerings**

The following ``describe-reserved-instances-offerings`` example describes all Reserved Instances available for purchase in the region. ::

    aws ec2 describe-reserved-instances-offerings

Output::

    {
        "ReservedInstancesOfferings": [
            {
                "OfferingType": "Partial Upfront",
                "AvailabilityZone": "us-west-2b",
                "InstanceTenancy": "default",
                "PricingDetails": [],
                "ProductDescription": "Red Hat Enterprise Linux",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "Amount": 0.088,
                        "Frequency": "Hourly"
                    }
                ],
                "Marketplace": false,
                "CurrencyCode": "USD",
                "FixedPrice": 631.0,
                "Duration": 94608000,
                "ReservedInstancesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "InstanceType": "c1.medium"
            },
            {
                "OfferingType": "PartialUpfront",
                "AvailabilityZone": "us-west-2b",
                "InstanceTenancy": "default",
                "PricingDetails": [],
                "ProductDescription": "Linux/UNIX",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "Amount": 0.028,
                        "Frequency": "Hourly"
                    }
                ],
                "Marketplace": false,
                "CurrencyCode": "USD",
                "FixedPrice": 631.0,
                "Duration": 94608000,
                "ReservedInstancesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "InstanceType": "c1.medium"
            }
        ]
    }

For more information, see `Buy Reserved Instances for Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe your Reserved Instances offerings using options**

The following ``describe-reserved-instances-offerings`` example lists Reserved Instances offered by AWS with the following specifications: t1.micro instance types, Windows (Amazon VPC) product, and No Upfront offerings. ::

    aws ec2 describe-reserved-instances-offerings \
        --no-include-marketplace \
        --instance-type "t1.micro" \
        --product-description "Windows (Amazon VPC)" \
        --offering-type "no upfront"

Output::

    {
        "ReservedInstancesOfferings": [
            {
                "OfferingType": "No Upfront",
                "AvailabilityZone": "us-west-2b",
                "InstanceTenancy": "default",
                "PricingDetails": [],
                "ProductDescription": "Windows",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "Amount": 0.015,
                        "Frequency": "Hourly"
                    }
                ],
                "Marketplace": false,
                "CurrencyCode": "USD",
                "FixedPrice": 0.0,
                "Duration": 31536000,
                "ReservedInstancesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "InstanceType": "t1.micro"
            },
            {
                "OfferingType": "No Upfront",
                "AvailabilityZone": "us-west-2d",
                "InstanceTenancy": "default",
                "PricingDetails": [],
                "ProductDescription": "Windows (Amazon VPC)",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "Amount": 0.015,
                        "Frequency": "Hourly"
                    }
                ],
                "Marketplace": false,
                "CurrencyCode": "USD",
                "FixedPrice": 0.0,
                "Duration": 31536000,
                "ReservedInstancesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "InstanceType": "t1.micro"
            }
        ]
    }

For more information, see `Buy Reserved Instances for Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html>`__ in the *Amazon EC2 User Guide*.

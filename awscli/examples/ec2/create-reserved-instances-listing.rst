**To list a Reserved Instance in the Reserved Instance Marketplace**

The following ``create-reserved-instances-listing`` example creates a listing for the specified Reserved Instance in the Reserved Instance Marketplace. ::

    aws ec2 create-reserved-instances-listing \
        --reserved-instances-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --instance-count 3 \
        --price-schedules CurrencyCode=USD,Price=25.50 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "ReservedInstancesListings": [
            {
                "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreateDate": "2024-05-14T18:12:30.000Z",
                "InstanceCounts": [
                    {
                        "InstanceCount": 3,
                        "State": "available"
                    },
                    {
                        "InstanceCount": 0,
                        "State": "sold"
                    },
                    {
                        "InstanceCount": 0,
                        "State": "cancelled"
                    },
                    {
                        "InstanceCount": 0,
                        "State": "pending"
                    }
                ],
                "PriceSchedules": [
                    {
                        "Active": true,
                        "CurrencyCode": "USD",
                        "Price": 25.5,
                        "Term": 11
                    }
                ],
                "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ReservedInstancesListingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "active",
                "StatusMessage": "active",
                "Tags": [],
                "UpdateDate": "2024-05-14T18:12:30.000Z"
            }
        ]
    }

For more information, see `Sell Reserved Instances for Amazon EC2 in the Reserved Instance Marketplace <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-general.html>`__ in the *Amazon EC2 User Guide*.

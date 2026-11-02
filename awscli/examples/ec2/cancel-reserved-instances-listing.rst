**To cancel a Reserved Instance listing**

The following ``cancel-reserved-instances-listing`` example cancels the specified Reserved Instance listing. ::

    aws ec2 cancel-reserved-instances-listing \
        --reserved-instances-listing-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ReservedInstancesListings": [
            {
                "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreateDate": "2024-05-14T18:12:30.000Z",
                "InstanceCounts": [
                    {
                        "InstanceCount": 0,
                        "State": "available"
                    },
                    {
                        "InstanceCount": 0,
                        "State": "sold"
                    },
                    {
                        "InstanceCount": 3,
                        "State": "cancelled"
                    },
                    {
                        "InstanceCount": 0,
                        "State": "pending"
                    }
                ],
                "PriceSchedules": [
                    {
                        "Active": false,
                        "CurrencyCode": "USD",
                        "Price": 25.5,
                        "Term": 11
                    }
                ],
                "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ReservedInstancesListingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Status": "cancelled",
                "StatusMessage": "cancelled",
                "Tags": [],
                "UpdateDate": "2024-05-15T09:24:51.000Z"
            }
        ]
    }

For more information, see `Sell Reserved Instances for Amazon EC2 in the Reserved Instance Marketplace <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-general.html>`__ in the *Amazon EC2 User Guide*.

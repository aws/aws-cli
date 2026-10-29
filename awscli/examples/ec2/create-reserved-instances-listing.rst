**To list a Reserved Instance in the Reserved Instance Marketplace**

The following ``create-reserved-instances-listing`` example creates a listing for the specified Reserved Instance in the Reserved Instance Marketplace. ::

    aws ec2 create-reserved-instances-listing \
        --reserved-instances-id 5ec28771-05ff-4b9b-aa31-9e57dexample \
        --instance-count 3 \
        --price-schedules CurrencyCode=USD,Price=25.50 \
        --client-token 550e8400-e29b-41d4-a716-446655440000

Output::

    {
        "ReservedInstancesListings": [
            {
                "ClientToken": "550e8400-e29b-41d4-a716-446655440000",
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
                "ReservedInstancesId": "5ec28771-05ff-4b9b-aa31-9e57dexample",
                "ReservedInstancesListingId": "8ba8f2f2-5ab8-4ac6-b6f1-1a2b3example",
                "Status": "active",
                "StatusMessage": "active",
                "Tags": [],
                "UpdateDate": "2024-05-14T18:12:30.000Z"
            }
        ]
    }

For more information, see `Sell Reserved Instances for Amazon EC2 in the Reserved Instance Marketplace <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-general.html>`__ in the *Amazon EC2 User Guide*.

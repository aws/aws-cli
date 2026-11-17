**To get a quote for exchanging a Convertible Reserved Instance**

The following ``get-reserved-instances-exchange-quote`` example gets the exchange information for the specified Convertible Reserved Instances. ::

    aws ec2 get-reserved-instances-exchange-quote \
        --reserved-instance-ids a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --target-configurations OfferingId=6fea5434-b379-434c-b07b-a7abexample

Output::

    {
        "CurrencyCode": "USD",
        "ReservedInstanceValueSet": [
            {
                "ReservedInstanceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ReservationValue": {
                    "RemainingUpfrontValue": "0.000000",
                    "HourlyPrice": "0.027800",
                    "RemainingTotalValue": "730.556200"
                }
            }
        ],
        "PaymentDue": "424.983828",
        "TargetConfigurationValueSet": [
            {
                "TargetConfiguration": {
                    "InstanceCount": 5,
                    "OfferingId": "6fea5434-b379-434c-b07b-a7abexample"
                },
                "ReservationValue": {
                    "RemainingUpfrontValue": "424.983828",
                    "HourlyPrice": "0.016000",
                    "RemainingTotalValue": "845.447828"
                }
            }
        ],
        "IsValidExchange": true,
        "OutputReservedInstancesWillExpireAt": "2020-10-01T13:03:39Z",
        "ReservedInstanceValueRollup": {
            "RemainingUpfrontValue": "0.000000",
            "HourlyPrice": "0.027800",
            "RemainingTotalValue": "730.556200"
        },
        "TargetConfigurationValueRollup": {
            "RemainingUpfrontValue": "424.983828",
            "HourlyPrice": "0.016000",
            "RemainingTotalValue": "845.447828"
        }
    }

For more information, see `Exchange Convertible Reserved Instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-convertible-exchange.html>`__ in the *Amazon EC2 User Guide*.

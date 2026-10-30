**To purchase a reserved node**

The following ``purchase-reserved-node-offering`` example purchases a reserved node offering. The ``reserved-node-offering-id`` is obtained by
calling ``describe-reserved-node-offerings``. ::

    aws redshift purchase-reserved-node-offering \
        --reserved-node-offering-id ceb6a579-cf4c-4343-be8b-d832c45ab51c

Output::

    {
        "ReservedNode": {
            "OfferingType": "Heavy Utilization",
            "FixedPrice": 3000.0,
            "NodeType": "dw.hs1.xlarge",
            "ReservedNodeId": "1ba8e2e3-bc01-4d65-b35d-a4a3e931547e",
            "UsagePrice": 0.0,
            "RecurringCharges": [
                {
                    "RecurringChargeAmount": 0.114,
                    "RecurringChargeFrequency": "Hourly"
                }
            ],
            "NodeCount": 1,
            "State": "payment-pending",
            "StartTime": "2013-02-13T17:08:39.051Z",
            "Duration": 31536000,
            "ReservedNodeOfferingId": "ceb6a579-cf4c-4343-be8b-d832c45ab51c"
        }
    }

For more information, see `Purchasing a reserved node <https://docs.aws.amazon.com/redshift/latest/mgmt/purchase-reserved-node-offering-console.html>`__ in the *Amazon Redshift Management Guide*.

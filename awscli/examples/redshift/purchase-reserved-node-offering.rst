**To purchase a reserved node**

The following ``purchase-reserved-node-offering`` example purchases a reserved node offering. The ``reserved-node-offering-id`` is obtained by
calling ``describe-reserved-node-offerings``. ::

    aws redshift purchase-reserved-node-offering \
        --reserved-node-offering-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ReservedNode": {
            "OfferingType": "Heavy Utilization",
            "FixedPrice": 3000.0,
            "NodeType": "dw.hs1.xlarge",
            "ReservedNodeId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
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
            "ReservedNodeOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

For more information, see `Purchasing a reserved node <https://docs.aws.amazon.com/redshift/latest/mgmt/purchase-reserved-node-offering-console.html>`__ in the *Amazon Redshift Management Guide*.

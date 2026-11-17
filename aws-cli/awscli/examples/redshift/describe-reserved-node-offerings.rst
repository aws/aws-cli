**To describe reserved node offerings**

The following ``describe-reserved-node-offerings`` example shows all of the reserved node offerings that are available for
purchase. ::

    aws redshift describe-reserved-node-offerings

Output::

    {
        "ReservedNodeOfferings": [
            {
                "OfferingType": "Heavy Utilization",
                "FixedPrice": 3000.0,
                "NodeType": "dw.hs1.xlarge",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.114,
                        "RecurringChargeFrequency": "Hourly"
                } ],
                "Duration": 31536000,
                "ReservedNodeOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "OfferingType": "Heavy Utilization",
                "FixedPrice": 24000.0,
                "NodeType": "dw.hs1.8xlarge",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.912,
                        "RecurringChargeFrequency": "Hourly"
                } ],
                "Duration": 31536000,
                "ReservedNodeOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

If you want to purchase a reserved node offering, you can call ``purchase-reserved-node-offering`` using a valid
*ReservedNodeOfferingId*.

For more information, see `Reserved nodes <https://docs.aws.amazon.com/redshift/latest/mgmt/purchase-reserved-node-instance.html>`__ in the *Amazon Redshift Management Guide*.

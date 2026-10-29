**To describe reserved nodes**

The following ``describe-reserved-nodes`` example shows a reserved node offering that has been purchased. ::

    aws redshift describe-reserved-nodes

Output::

    {
        "ReservedNodes": [
            {
                "OfferingType": "Heavy Utilization",
                "FixedPrice": 3000.0,
                "NodeType": "dw.hs1.xlarge",
                "ReservedNodeId": "1ba8e2e3-bc01-4d65-b35d-a4a3e931547e",
                "UsagePrice": 0.0,
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.21,
                        "RecurringChargeFrequency": "Hourly"
                    } ],
                "NodeCount": 1,
                "State": "payment-pending",
                "StartTime": "2013-02-13T17:08:39.051Z",
                "Duration": 31536000,
                "ReservedNodeOfferingId": "ceb6a579-cf4c-4343-be8b-d832c45ab51c"
            }
        ]
    }

For more information, see `Reserved nodes <https://docs.aws.amazon.com/redshift/latest/mgmt/purchase-reserved-node-instance.html>`__ in the *Amazon Redshift Management Guide*.

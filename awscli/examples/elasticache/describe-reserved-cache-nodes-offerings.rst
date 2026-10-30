**To describe reserved-cache-nodes-offerings**

The following ``describe-reserved-cache-nodes-offerings`` example returns details of a reserved-cache-node options. ::

    aws elasticache describe-reserved-cache-nodes-offerings

Output::

    {
        "ReservedCacheNodesOfferings": [
            {
                "ReservedCacheNodesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CacheNodeType": "cache.t3.small",
                "Duration": 31536000,
                "FixedPrice": 97.0,
                "UsagePrice": 0.0,
                "ProductDescription": "memcached",
                "OfferingType": "Partial Upfront",
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.011,
                        "RecurringChargeFrequency": "Hourly"
                    }
                ]
            },
            {
                "ReservedCacheNodesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CacheNodeType": "cache.m3.2xlarge",
                "Duration": 31536000,
                "FixedPrice": 1772.0,
                "UsagePrice": 0.0,
                "ProductDescription": "redis",
                "OfferingType": "Heavy Utilization",
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.25,
                        "RecurringChargeFrequency": "Hourly"
                    }
                ]
            }
        ]
    }

For more information, see `Reserved nodes <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheNodes.Reserved.html>`__ in the *Elasticache User Guide*.

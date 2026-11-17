**To describe reserved DB instance offerings**

The following ``describe-reserved-db-instances-offerings`` example retrieves details about reserved DB instance options for ``oracle``. ::

    aws rds describe-reserved-db-instances-offerings \
        --product-description oracle

Output::

    {
        "ReservedDBInstancesOfferings": [
            {
                "CurrencyCode": "USD",
                "UsagePrice": 0.0,
                "ProductDescription": "oracle-se2(li)",
                "ReservedDBInstancesOfferingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "MultiAZ": true,
                "DBInstanceClass": "db.m4.xlarge",
                "OfferingType": "Partial Upfront",
                "RecurringCharges": [
                    {
                        "RecurringChargeAmount": 0.594,
                        "RecurringChargeFrequency": "Hourly"
                    }
                ],
                "FixedPrice": 4089.0,
                "Duration": 31536000
            }
        ]
    }

For more information, see `Reserved DB instances for Amazon RDS <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html>`__ in the *Amazon RDS User Guide*.

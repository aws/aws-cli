**To view all reserved instances**

The following ``describe-reserved-elasticsearch-instances`` example provides a summary of all instances you have reserved in a region. ::

    aws es describe-reserved-elasticsearch-instances

Output::

    {
        "ReservedElasticsearchInstances": [{
            "FixedPrice": 100.0,
            "ReservedElasticsearchInstanceOfferingId": "1a2a3a4a5-1a2a-3a4a-5a6a-1a2a3a4a5a6a",
            "ReservationName": "my-reservation",
            "PaymentOption": "PARTIAL_UPFRONT",
            "UsagePrice": 0.0,
            "ReservedElasticsearchInstanceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "RecurringCharges": [{
                "RecurringChargeAmount": 0.603,
                "RecurringChargeFrequency": "Hourly"
            }],
            "State": "payment-pending",
            "StartTime": 1522872571.229,
            "ElasticsearchInstanceCount": 3,
            "Duration": 31536000,
            "ElasticsearchInstanceType": "m4.2xlarge.elasticsearch",
            "CurrencyCode": "USD"
        }]
    }

For more information, see `Reserved Instances <https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/aes-ri.html>`__ in the *Amazon Elasticsearch Service Developer Guide*.

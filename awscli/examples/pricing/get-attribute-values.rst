**To retrieve a list of attribute values**

The following ``get-attribute-values`` example retrieves a list of values available for the given attribute. ::

    aws pricing get-attribute-values \
        --service-code AmazonEC2 \
        --attribute-name volumeType \
        --max-items 2

Output::

    {
        "NextToken": "eyJOZXh0VG9rZW4iOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQiOiAyfQ==",
        "AttributeValues": [
            {
                "Value": "Cold HDD"
            },
            {
                "Value": "General Purpose"
            }
        ]
    }

For more information, see `Finding services and products using AWS Price List Query API <https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-price-list-query-api.html>`__ in the *AWS Billing User Guide*.

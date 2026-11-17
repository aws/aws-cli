**To list tags for a data store**

The following ``list-tags-for-resource`` example lists the tags associated with the specified data store. ::

    aws healthlake list-tags-for-resource \
        --resource-arn "arn:aws:healthlake:us-west-2:123456789012:datastore/fhir/0725c83f4307f263e16fd56b6d8ebdbe"

Output::

    {
        "Tags": [
            {
                "Key": "key",
                "Value": "value"
            },
            {
                "Key": "key1",
                "Value": "value1"
            }
        ]
    }

For more information, see `Tagging HealthLake data stores <https://docs.aws.amazon.com/healthlake/latest/devguide/managing-data-stores-tagging.html>`__ in the *AWS HealthLake Developer Guide*.

**To add a tag to data store**

The following ``tag-resource`` example shows how to add a tag to a data store. ::

    aws healthlake tag-resource \
        --resource-arn "arn:aws:healthlake:us-west-2:123456789012:datastore/fhir/0725c83f4307f263e16fd56b6d8ebdbe" \
        --tags '[{"Key": "key1", "Value": "value1"}]'

This command produces no output.

For more information, see `Tagging HealthLake data stores <https://docs.aws.amazon.com/healthlake/latest/devguide/managing-data-stores-tagging.html#tagresource>`__ in the *AWS HealthLake Developer Guide*.

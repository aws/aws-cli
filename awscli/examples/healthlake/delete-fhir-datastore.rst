**To delete a FHIR data store**

The following ``delete-fhir-datastore`` example demonstrates how to delete a data store and all of its contents in AWS HealthLake. ::

    aws healthlake delete-fhir-datastore \
        --datastore-id (Data store ID)

Output::

    {
        "DatastoreEndpoint": "https://healthlake.us-west-2.amazonaws.com/datastore/(Data store ID)/r4/",
        "DatastoreArn": "arn:aws:healthlake:us-west-2:(AWS Account ID):datastore/(Data store ID)",
        "DatastoreStatus": "DELETING",
        "DatastoreId": "(Data store ID)"
    }

For more information, see `Deleting a HealthLake data store <https://docs.aws.amazon.com/healthlake/latest/devguide/managing-data-stores-delete.html>`__ in the *AWS HealthLake Developer Guide*.

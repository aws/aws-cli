**To delete a FHIR data store**

The following ``delete-fhir-datastore`` example demonstrates how to delete a data store and all of its contents in AWS HealthLake. ::

    aws healthlake delete-fhir-datastore \
        --datastore-id a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

Output::

    {
        "DatastoreEndpoint": "https://healthlake.us-west-2.amazonaws.com/datastore/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6/r4/",
        "DatastoreArn": "arn:aws:healthlake:us-west-2:123456789012:datastore/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        "DatastoreStatus": "DELETING",
        "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    }

For more information, see `Deleting a HealthLake data store <https://docs.aws.amazon.com/healthlake/latest/devguide/managing-data-stores-delete.html>`__ in the *AWS HealthLake Developer Guide*.

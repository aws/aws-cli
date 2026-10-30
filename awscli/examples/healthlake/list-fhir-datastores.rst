**To list FHIR data stores**

The following ``list-fhir-datastores`` example shows to how to use the command and how users can filter results based on data store status in AWS HealthLake. ::

    aws healthlake list-fhir-datastores \
        --filter DatastoreStatus=ACTIVE

Output::

    {
        "DatastorePropertiesList": [
        {
            "PreloadDataConfig": {
                "PreloadDataType": "SYNTHEA"
            },
            "SseConfiguration": {
                "KmsEncryptionConfig": {
                    "CmkType": "CUSTOMER_MANAGED_KMS_KEY",
                    "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                }
            },
            "DatastoreName": "Demo",
            "DatastoreArn": "arn:aws:healthlake:us-west-2:123456789012:datastore/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            "DatastoreEndpoint": "https://healthlake.us-west-2.amazonaws.com/datastore/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6/r4/",
            "DatastoreStatus": "ACTIVE",
            "DatastoreTypeVersion": "R4",
            "CreatedAt": 1603761064.881,
            "DatastoreId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            "IdentityProviderConfiguration": {
                "AuthorizationStrategy": "AWS_AUTH",
                "FineGrainedAuthorizationEnabled": false
            }
        }
        ]
    }

For more information, see `Listing HealthLake data stores <https://docs.aws.amazon.com/healthlake/latest/devguide/managing-data-stores-list.html>`__ in the *AWS HealthLake Developer Guide*.

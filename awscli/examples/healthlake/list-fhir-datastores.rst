**To list FHIR Data Stores**

The following ``list-fhir-datastores`` example shows to how to use the command and how users can filter results based on Data Store status in Amazon HealthLake. ::

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
                    "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                }
            },
            "DatastoreName": "Demo",
            "DatastoreArn": "arn:aws:healthlake:us-east-1:<AWS Account ID>:datastore/<Datastore ID>",
            "DatastoreEndpoint": "https://healthlake.us-east-1.amazonaws.com/datastore/<Datastore ID>/r4/",
            "DatastoreStatus": "ACTIVE",
            "DatastoreTypeVersion": "R4",
            "CreatedAt": 1603761064.881,
            "DatastoreId": "<Datastore ID>",
            "IdentityProviderConfiguration": {
                "AuthorizationStrategy": "AWS_AUTH",
                "FineGrainedAuthorizationEnabled": false
            }
        }
        ]
    }

For more information, see `Creating and monitoring a FHIR Data Store <https://docs.aws.amazon.com/healthlake/latest/devguide/working-with-FHIR-healthlake.html>`__ in the *Amazon HealthLake Developer Guide*.

**To describe a FHIR Data Store**

The following ``describe-fhir-datastore`` example demonstrates how to find the properties of a Data Store in Amazon HealthLake. ::

    aws healthlake describe-fhir-datastore \
        --datastore-id "1f2f459836ac6c513ce899f9e4f66a59"


Output::

    {
        "DatastoreProperties": {
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
    }

For more information, see `Creating and monitoring a FHIR Data Stores <https://docs.aws.amazon.com/healthlake/latest/devguide/working-with-FHIR-healthlake.html>`__ in the *Amazon HealthLake Developer Guide*.

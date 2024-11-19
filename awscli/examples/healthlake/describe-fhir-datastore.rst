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
            "DatastoreName": "FhirTestDatastore",
            "DatastoreArn": "arn:aws:healthlake:us-east-1:(AWS Account ID):datastore/(Datastore ID)",
            "DatastoreEndpoint": "https://healthlake.us-east-1.amazonaws.com/datastore/(Datastore ID)/r4/",
            "DatastoreStatus": "CREATING",
            "DatastoreTypeVersion": "R4",
            "DatastoreId": "(Datastore ID)"
            "CreatedAt": "2024-11-18T14:42:53.467000-05:00",
            "SseConfiguration": {
                "KmsEncryptionConfig": {
                    "CmkType": "AWS_OWNED_KMS_KEY"
                }
            },
            "IdentityProviderConfiguration": {
                "AuthorizationStrategy": "AWS_AUTH",
                "FineGrainedAuthorizationEnabled": false
            }
        }
    }

For more information, see `Creating and monitoring a FHIR Data Stores <https://docs.aws.amazon.com/healthlake/latest/devguide/working-with-FHIR-healthlake.html>`__ in the *Amazon HealthLake Developer Guide*.

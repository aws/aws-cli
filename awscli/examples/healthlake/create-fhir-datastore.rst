**To create a FHIR Data Store.**

The following ``create-fhir-datastore`` example demonstrates how to create a new Data Store in Amazon HealthLake. ::

**Example 1: Create a SigV4-enabled HealthLake data store**

    aws healthlake create-fhir-datastore \
        --datastore-type-version R4 \
        --datastore-name "FhirTestDatastore"

Output::

    {
        "DatastoreEndpoint": "https://healthlake.us-east-1.amazonaws.com/datastore/(Datastore ID)/r4/",
        "DatastoreArn": "arn:aws:healthlake:us-east-1:(AWS Account ID):datastore/(Datastore ID)",
        "DatastoreStatus": "CREATING",
        "DatastoreId": "(Datastore ID)"
    }

**Example 2: Create a SMART on FHIR-enabled HealthLake data store**

    aws healthlake create-fhir-datastore \
        --datastore-name "your-data-store-name" \
        --datastore-type-version R4 \
        --preload-data-config PreloadDataType="SYNTHEA" \
        --sse-configuration '{ "KmsEncryptionConfig": {  "CmkType": "CUSTOMER_MANAGED_KMS_KEY", "KmsKeyId": "arn:aws:kms:us-east-1:your-account-id:key/your-key-id" } }' \
        --identity-provider-configuration  file://identity_provider_configuration.json

Contents of ``identity_provider_configuration.json``::

    {
      "AuthorizationStrategy": "SMART_ON_FHIR_V1",
      "FineGrainedAuthorizationEnabled": true,
      "IdpLambdaArn": "arn:aws:lambda:your-region:your-account-id:function:your-lambda-name",
      "Metadata": "{\"issuer\":\"https://ehr.example.com\", \"jwks_uri\":\"https://ehr.example.com/.well-known/jwks.json\",\"authorization_endpoint\":\"https://ehr.example.com/auth/authorize\",\"token_endpoint\":\"https://ehr.token.com/auth/token\",\"token_endpoint_auth_methods_supported\":[\"client_secret_basic\",\"foo\"],\"grant_types_supported\":[\"client_credential\",\"foo\"],\"registration_endpoint\":\"https://ehr.example.com/auth/register\",\"scopes_supported\":[\"openId\",\"profile\",\"launch\"],\"response_types_supported\":[\"code\"],\"management_endpoint\":\"https://ehr.example.com/user/manage\",\"introspection_endpoint\":\"https://ehr.example.com/user/introspect\",\"revocation_endpoint\":\"https://ehr.example.com/user/revoke\",\"code_challenge_methods_supported\":[\"S256\"],\"capabilities\":[\"launch-ehr\",\"sso-openid-connect\",\"client-public\"]}"
    }

Output::

    {
        "DatastoreEndpoint": "https://healthlake.us-east-1.amazonaws.com/datastore/(Datastore ID)/r4/",
        "DatastoreArn": "arn:aws:healthlake:us-east-1:(AWS Account ID):datastore/(Datastore ID)",
        "DatastoreStatus": "CREATING",
        "DatastoreId": "(Datastore ID)"
    }


For more information, see `Creating and monitoring a FHIR Data Store <https://docs.aws.amazon.com/healthlake/latest/devguide/working-with-FHIR-healthlake.html>`__ in the *Amazon HealthLake Developer Guide*.

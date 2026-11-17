**To retrieve hosted configuration details**

The following ``get-hosted-configuration-version`` example retrieves the configuration details of the AWS AppConfig hosted configuration. ::

    aws appconfig get-hosted-configuration-version hosted-configuration-version-output \
        --application-id 339ohji \
        --configuration-profile-id ur8hx2f \
        --version-number 1

Contents of ``hosted-configuration-version-output``::

    { "Name": "ExampleApplication", "Id": ExampleID, "Rank": 7 }

Output::

    {
        "ApplicationId": "339ohji",
        "ConfigurationProfileId": "ur8hx2f",
        "VersionNumber": 1,
        "ContentType": "application/json"
    }

For more information, see `About the AWS AppConfig hosted configuration store <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-profile-about-hosted-store.html>`__ in the *AWS AppConfig User Guide*.
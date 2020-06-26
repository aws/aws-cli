**To list the AppConfig applications in your AWS account**

This ``get-configuration`` example lists the applications in your account in the current Region. ::

    aws appconfig get-configuration \
        --application abc1234 \
        --environment 9x8y7z6 \
        --configuration 9sd1ukd \
        --client-id any-id \
        outfile_name

Output::

    {
        "ConfigurationVersion": "2",
        "ContentType": "application/octet-stream"
    }  

For more information, see `Retrieving the Configuration <https://docs.aws.amazon.com/systems-manager/latest/userguide/appconfig-retrieving-the-configuration.html>`__ in the *AWS Systems Manager User Guide*.

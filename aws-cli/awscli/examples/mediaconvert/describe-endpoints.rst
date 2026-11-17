**To get your account-specific endpoint**

The following ``describe-endpoints`` example retrieves the endpoint that you need to send any other request to the service. ::

    aws mediaconvert describe-endpoints

Output::

    {
        "Endpoints": [
            {
                "Url": "https://abcd1234.mediaconvert.region-name-1.amazonaws.com"
            }
        ]
    }

For more information, see `Getting started with MediaConvert <https://docs.aws.amazon.com/mediaconvert/latest/ug/getting-started.html>`__ in the *AWS Elemental MediaConvert User Guide*.

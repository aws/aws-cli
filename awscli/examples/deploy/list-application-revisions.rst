**To get information about application revisions**

The following ``list-application-revisions`` example displays information about all application revisions that are associated with the specified application. ::

    aws deploy list-application-revisions \
        --application-name WordPress_App \
        --s-3-bucket amzn-s3-demo-bucket \
        --deployed exclude \
        --s-3-key-prefix WordPress_ \
        --sort-by lastUsedTime \
        --sort-order descending

Output::

    {
        "revisions": [
            {
                "revisionType": "S3",
                "s3Location": {
                    "version": "uTecLusvCB_JqHFXtfUcyfV8bEXAMPLE",
                    "bucket": "amzn-s3-demo-bucket",
                    "key": "WordPress_App.zip",
                    "bundleType": "zip"
                }
            },
            {
                "revisionType": "S3",
                "s3Location": {
                    "version": "tMk.UxgDpMEVb7V187ZM6wVAWEXAMPLE",
                    "bucket": "amzn-s3-demo-bucket",
                    "key": "WordPress_App_2-0.zip",
                    "bundleType": "zip"
                }
            }
        ]
    }

**To display details about a signing platform**

The following ``get-signing-platform`` example displays details about the specified signing platform. ::

    aws signer get-signing-platform \
        --platform-id AmazonFreeRTOS-TI-CC3220SF

Output::

    {
        "category": "AWS",
        "displayName": "Amazon FreeRTOS SHA1-RSA CC3220SF-Format",
        "target": "SHA1-RSA-TISHA1",
        "platformId": "AmazonFreeRTOS-TI-CC3220SF",
        "signingConfiguration": {
            "encryptionAlgorithmOptions": {
                "defaultValue": "RSA",
                "allowedValues": [
                    "RSA"
                ]
            },
            "hashAlgorithmOptions": {
                "defaultValue": "SHA1",
                "allowedValues": [
                    "SHA1"
                ]
            }
        },
        "maxSizeInMB": 16,
        "partner": "AmazonFreeRTOS",
        "signingImageFormat": {
            "defaultFormat": "JSONEmbedded",
            "supportedFormats": [
                "JSONEmbedded"
            ]
        }
    }

For more information, see `Sign Internet of Things (IoT) objects <https://docs.aws.amazon.com/signer/latest/developerguide/iot-workflow.html>`__ in the *AWS Signer Developer Guide*.

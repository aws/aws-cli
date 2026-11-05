**Example 1: To add a CORS policy**

The following ``put-cors-policy`` example adds a cross-origin resource sharing (CORS) policy to the specified container. The contents of the CORS policy are in the file named ``corsPolicy.json``. ::

    aws mediastore put-cors-policy \
        --container-name ExampleContainer \
        --cors-policy file://corsPolicy.json

Contents of ``corsPolicy.json``::

    [
        {
            "AllowedOrigins": [
                "https://www.example.com"
            ],
            "AllowedMethods": [
                "GET",
                "HEAD"
            ],
            "AllowedHeaders": [
                "*"
            ],
            "MaxAgeSeconds": 3000
        }
    ]

This command produces no output.

**Example 2: To edit a CORS policy**

The following ``put-cors-policy`` example updates the cross-origin resource sharing (CORS) policy that is assigned to the specified container. The contents of the updated CORS policy are in the file named ``corsPolicy2.json``.

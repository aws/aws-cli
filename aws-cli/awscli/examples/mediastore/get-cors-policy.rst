**To view a CORS policy**

The following ``get-cors-policy`` example displays the cross-origin resource sharing (CORS) policy that is assigned to the specified container. ::

    aws mediastore get-cors-policy \
        --container-name ExampleContainer

Output::

    {
        "CorsPolicy": [
            {
                "AllowedMethods": [
                    "GET",
                    "HEAD"
                ],
                "MaxAgeSeconds": 3000,
                "AllowedOrigins": [
                    ""
                ],
                "AllowedHeaders": [
                    ""
                ]
            }
        ]
    }

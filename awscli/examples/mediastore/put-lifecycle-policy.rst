**To create an object lifecycle policy**

The following ``put-lifecycle-policy`` example attaches an object lifecycle policy to the specified container. This enables you to specify how long the service should store objects in your container. MediaStore deletes objects in the container once they reach their expiration date, as indicated in the policy, which is in the file named ``ExampleLifecyclePolicy.json``. ::

    aws mediastore put-lifecycle-policy \
        --container-name ExampleContainer \
        --lifecycle-policy file://ExampleLifecyclePolicy.json

Contents of ``ExampleLifecyclePolicy.json``::

    {
        "rules": [
            {
                "definition": {
                    "path": [
                        {"prefix": "Football/"},
                        {"prefix": "Baseball/"}
                    ],
                    "days_since_create": [
                        {"numeric": [">", 28]}
                    ]
                },
                "action": "EXPIRE"
            }
        ]
    }

This command produces no output.

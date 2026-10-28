**To temporarily modify the quota on an API key for the current period defined in the Usage Plan**

The following ``update-usage`` example temporarily modifies the quota on an API key for the current period defined in the Usage Plan. ::

    aws apigateway update-usage \
        --usage-plan-id a1b2c3 \
        --key-id 1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu \
        --patch-operations op="replace",path="/remaining",value="50"

Output::

    {
        "usagePlanId": "a1b2c3",
        "startDate": "2016-08-16",
        "endDate": "2016-08-16",
        "items": {
            "1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu": [
                [
                    0,
                    50
                ]
            ]
        }
    }

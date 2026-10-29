**To list all of the discovered servers meeting a set of filter conditions**

The following ``list-configurations`` example lists discovered servers matching either of two hostname patterns and not running Ubuntu. ::

    aws discovery list-configurations \
        --configuration-type SERVER \
        --filters name="server.hostName",values="172-31-35","172-31-42",condition="CONTAINS" name="server.osName",values="Ubuntu",condition="NOT_CONTAINS"

Output::

    {
        "configurations": [
            {
                "server.osVersion": "3.14.48-33.39.amzn1.x86_64",
                "server.type": "EC2",
                "server.hostName": "ip-172-31-42-208",
                "server.timeOfCreation": "2016-10-28 23:44:30.0",
                "server.configurationId": "d-server-099385097ef9fbcfb",
                "server.osName": "Linux - Amazon Linux AMI release 2015.03",
                "server.agentId": "i-c142b99e"
            },
            {
                "server.osVersion": "3.14.48-33.39.amzn1.x86_64",
                "server.type": "EC2",
                "server.hostName": "ip-172-31-35-152",
                "server.timeOfCreation": "2016-10-28 23:44:00.0",
                "server.configurationId": "d-server-0c4f2dd1fee22c6c1",
                "server.osName": "Linux - Amazon Linux AMI release 2015.03",
                "server.agentId": "i-4447bc1b"
            }
        ]
    }

For more information, see `Using the Application Discovery Service API to query discovered configuration items <https://docs.aws.amazon.com/application-discovery/latest/userguide/discovery-api-queries.html>`__ in the *AWS Application Discovery Service User Guide*.

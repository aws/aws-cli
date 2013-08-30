**To describe Elastic IPs**

The following ``describe-elastic-ips`` commmand describes the Elastic IP addresses in an instance, whose ID is
``b62f3e04-e9eb-436c-a91f-d9e9a396b7b0``::

  aws opsworks describe-elastic-ips --instance-id b62f3e04-e9eb-436c-a91f-d9e9a396b7b0

Output::

  {
    "ElasticIps": [
        {
            "Ip": "54.214.246.6",
            "Domain": "standard",
            "Region": "us-west-2"
        }
    ]
  }

For more information, see Instances_ in the *OpsWorks User Guide*.

.. _Instances: http://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances.html


**To describe instances**

The following ``describe-instances`` commmand describes the instances in a stack, whose ID is
``38ee91e2-abdc-4208-a107-0b7168b3cc7a``::

  aws opsworks describe-instances --stack-id 38ee91e2-abdc-4208-a107-0b7168b3cc7a

Output::

  {
    "Instances": [
        {
            "StackId": "38ee91e2-abdc-4208-a107-0b7168b3cc7a",
            "SshHostRsaKeyFingerprint": "f4:3b:8e:27:1b:73:98:80:5d:d7:33:e2:b8:c8:8f:de",
            "Status": "stopped",
            "AvailabilityZone": "us-west-2a",
            "SshHostDsaKeyFingerprint": "e8:9b:c7:02:18:2a:bd:ab:45:89:21:4e:af:0b:07:ac",
            "InstanceId": "8c2673b9-3fe5-420d-9cfa-78d875ee7687",
            "Os": "Amazon Linux",
            "Hostname": "db-master1",
            "SecurityGroupIds": [],
            "Architecture": "x86_64",
            "RootDeviceType": "instance-store",
            "LayerIds": [
                "41a20847-d594-4325-8447-171821916b73"
            ],
            "InstanceType": "c1.medium",
            "CreatedAt": "2013-07-25T18:11:27+00:00"
        },
        {
            "StackId": "38ee91e2-abdc-4208-a107-0b7168b3cc7a",
            "SshHostRsaKeyFingerprint": "ae:3a:85:54:66:f3:ce:98:d9:83:39:1e:10:a9:38:12",
            "Status": "stopped",
            "AvailabilityZone": "us-west-2a",
            "SshHostDsaKeyFingerprint": "5b:b9:6f:5b:1c:ec:55:85:f3:45:f1:28:25:1f:de:e4",
            "InstanceId": "9e588a25-35b2-4804-bd43-488f85ebe5b7",
            "Os": "Amazon Linux",
            "Hostname": "tomcustom1",
            "SecurityGroupIds": [],
            "Architecture": "x86_64",
            "RootDeviceType": "instance-store",
            "LayerIds": [
                "e6cbcd29-d223-40fc-8243-2eb213377440"
            ],
            "InstanceType": "c1.medium",
            "CreatedAt": "2013-07-25T18:15:52+00:00"
        }
    ]
  }

For more information, see Instances_ in the *OpsWorks User Guide*.

.. _Instances: http://docs.aws.amazon.com/opsworks/latest/userguide/workinginstances.html


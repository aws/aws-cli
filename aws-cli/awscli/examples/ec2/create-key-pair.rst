**To create a key pair**

The following ``create-key-pair`` example creates a key pair named ``MyKeyPair``. ::

    aws ec2 create-key-pair \
        --key-name MyKeyPair

The output is an ASCII version of the private key and key fingerprint. You need to save the key to a file.

Output::

    {
        "KeyFingerprint": "1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca:9f:f5:f1:6f",
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----\nEXAMPLEKEYMATERIAL\n-----END RSA PRIVATE KEY-----",
        "KeyName": "MyKeyPair",
        "KeyPairId": "key-0b94643da6EXAMPLE"
    }

For more information, see `Creating, displaying, and deleting Amazon EC2 key pairs in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-keypairs.html>`__ in the *AWS Command Line Interface User Guide*.

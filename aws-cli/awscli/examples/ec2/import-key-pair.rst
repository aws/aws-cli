**To import a public key**

The following ``import-key-pair`` example imports a public key. First, generate a key pair with the tool of your choice. For example, use the following ``ssh-keygen`` command. ::

    ssh-keygen -t rsa -C "my-key" -f ~/.ssh/my-key

The ``ssh-keygen`` command displays output similar to the following::

    Generating public/private rsa key pair.
    Enter passphrase (empty for no passphrase):
    Enter same passphrase again:
    Your identification has been saved in /home/ec2-user/.ssh/my-key.
    Your public key has been saved in /home/ec2-user/.ssh/my-key.pub.
    ...

The following command imports the specified public key. ::

    aws ec2 import-key-pair \
        --key-name "my-key" \
        --public-key-material fileb://~/.ssh/my-key.pub

Output::

    {
        "KeyName": "my-key",
        "KeyFingerprint": "1f:51:ae:28:bf:89:e9:d8:1f:25:5d:37:2d:7d:b8:ca"
    }

For more information, see `Create a key pair for your Amazon EC2 instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html#how-to-generate-your-own-key-and-import-it-to-aws>`__ in the *Amazon EC2 User Guide*.

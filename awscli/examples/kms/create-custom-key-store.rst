**To create a custom key store**

The following ``create-custom-key-store`` example creates a custom key store backed by an AWS CloudHSM cluster.

To specify the file input for the ``trust-anchor-certificate`` command in the AWS CLI, the ``file://`` prefix is required. ::

    aws kms create-custom-key-store \
        --custom-key-store-name ExampleKeyStore \
        --cloud-hsm-cluster-id cluster-1a23b4cdefg \
        --key-store-password kmsPswd \
        --trust-anchor-certificate file://customerCA.crt

Output::

    {
        "CustomKeyStoreId": cks-1234567890abcdef0
    }

For more information, see `Creating a Custom Key Store <https://docs.aws.amazon.com/kms/latest/developerguide/create-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
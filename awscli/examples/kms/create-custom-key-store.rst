**To create a custom key store**

The following ``create-custom-key-store`` example creates a custom key store with an existing custom key store.

* This example uses the ``custom-key-store-name`` parameter to assign ``ExampleKeyStore`` as a friendly name for the key store.

* It uses the ``cloud-hsm-cluster-id`` parameter to identify the ``cluster-1a23b4cdefg`` cluster.

* It uses the ``key-store-password`` parameter to provide the password of the ``kmsuser`` user in the ``cluster-1a23b4cdefg`` cluster. This gives AWS KMS permission to use the cluster on your behalf.

* It uses the ``trust-anchor-certificate`` parameter to specify the ``customerCA.crt`` file. In the AWS CLI, the ``file://`` prefix is required. ::

    aws kms create-custom-key-store \
        --custom-key-store-name ExampleKeyStore \
        --cloud-hsm-cluster-id cluster-1a23b4cdefg \
        --key-store-password kmsPswd \
        --trust-anchor-certificate file://customerCA.crt

The output of this command includes the ID of the new custom key store. You can use this ID to identify the custom key store in other AWS KMS CLI commands. ::

    {
        "CustomKeyStoreId": cks-1234567890abcdef0
    }

For more information, see `Creating a Custom Key Store <https://docs.aws.amazon.com/kms/latest/developerguide/create-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.
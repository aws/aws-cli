**To get details about a custom key store**

The following ``describe-custom-key-store`` example displays details for the specified custom key store. You can use this command to get details about a particular custom key store or all custom key stores in an AWS account and Region.

To identify a particular custom key store, this example uses the ``custom-key-store-name`` parameter with the key store name. If you prefer, you can use the ``custom-key-store-id`` parameter with the key store ID. To get all custom key stores in the account and Region, omit all parameters. ::

    aws kms describe-custom-key-stores \
        --custom-key-store-name ExampleKeyStore

The output of this command includes useful details about the custom key store including its connection state (``ConnectionState``). If the connection state is ``FAILED``, the output includes a ``ConnectionErrorCode`` field that describes the problem. ::

    {
        "CustomKeyStores": [ 
            { 
                "CloudHsmClusterId": "cluster-1a23b4cdefg",
                "ConnectionState": "CONNECTED",
                "CreationDate": "1.599288695918E9",
                "CustomKeyStoreId": "cks-1234567890abcdef0",
                "CustomKeyStoreName": "ExampleKeyStore",
                "TrustAnchorCertificate": "<certificate appears here>"
            }
        ]
    }

For more information, see `Viewing a Custom Key Store <https://docs.aws.amazon.com/kms/latest/developerguide/view-keystore.html>`__ in the *AWS Key Management Service Developer Guide*.

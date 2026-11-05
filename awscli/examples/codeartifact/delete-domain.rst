**To delete a domain**

The following ``delete-domain`` example deletes a domain named ``test-domain``. ::

    aws codeartifact delete-domain \
        --domain test-domain

Output::

    {
        "domain": {
            "name": "test-domain",
            "owner": "123456789012",
            "arn": "arn:aws:codeartifact:us-west-2:123456789012:domain/test-domain",
            "status": "Deleted",
            "createdTime": "2020-10-20T13:16:48.559000-04:00",
            "encryptionKey": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "repositoryCount": 0,
            "assetSizeBytes": 0
        }
    }

For more information, see `Delete a domain <https://docs.aws.amazon.com/codeartifact/latest/ug/delete-domain.html>`__ in the *AWS CodeArtifact User Guide*.
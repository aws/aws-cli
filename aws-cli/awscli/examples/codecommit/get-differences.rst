**To get information about differences for a commit specifier in a repository**

The following ``get-differences`` example displays metadata information about changes between two commit specifiers (branch, tag, HEAD, or other fully qualified references, such as commit IDs) in a renamed folder in AWS CodeCommit repository named MyDemoRepo. The example includes several options that are not required, including ``--before-commit-specifier``, ``--before-path``, and ``--after-path``, in order to more fully illustrate how you can use these options to limit the results. The response includes file mode permissions. ::

    aws codecommit get-differences \
        --repository-name MyDemoRepo \
        --before-commit-specifier 955bba12thisisanexamplethisisanexample \
        --after-commit-specifier 14a95463thisisanexamplethisisanexample \
        --before-path tmp/example-folder \
        --after-path tmp/renamed-folder

Output::

    {
        "differences": [
            {
                "afterBlob": {
                    "path": "blob.txt",
                    "blobId": "2eb4af3b1thisisanexamplethisisanexample1",
                    "mode": "100644"
                },
                "changeType": "M",
                "beforeBlob": {
                    "path": "blob.txt",
                    "blobId": "bf7fcf281thisisanexamplethisisanexample1",
                    "mode": "100644"
                }
            }
        ]
    }

For more information, see `Compare commits in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-compare-commits.html>`__ in the *AWS CodeCommit User Guide*.

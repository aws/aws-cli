**To add a tag to a server certificate**

The following ``tag-server-certificate`` example adds a tag with a Department name to the specified server certificate. ::

    aws iam tag-server-certificate \
        --server-certificate-name ExampleCertificate \
        --tags '[{"Key": "Department", "Value": "Accounting"}]'

This command produces no output.

For more information, see `Tagging IAM resources <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_tags.html>`__ in the *AWS IAM User Guide*.
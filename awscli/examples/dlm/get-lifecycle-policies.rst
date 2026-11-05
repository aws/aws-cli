**To get a summary of your lifecycle policies**

The following ``get-lifecycle-policies`` example lists all of your lifecycle policies. ::

    aws dlm get-lifecycle-policies

Output::

    {
        "Policies": [
            {
                "PolicyId": "policy-0123456789abcdef0",
                "Description": "My first policy",
                "State": "ENABLED"
            }
        ]
    }

For more information, see `Automate backups with Amazon Data Lifecycle Manager <https://docs.aws.amazon.com/ebs/latest/userguide/snapshot-lifecycle.html>`__ in the *Amazon EBS User Guide*.

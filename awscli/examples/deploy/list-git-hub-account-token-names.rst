**To lists the names of stored connections to GitHub accounts**

The following ``list-git-hub-account-token-names`` example lists the names of the stored connections to GitHub accounts for the current AWS user. ::

    aws deploy list-git-hub-account-token-names

Output::

    {
        "tokenNameList": [
            "my-first-token",
            "my-second-token",
            "my-third-token"
        ]
    }

For more information, see `Integrating CodeDeploy with GitHub <https://docs.aws.amazon.com/codedeploy/latest/userguide/integrations-partners-github.html>`__ in the *AWS CodeDeploy User Guide*.

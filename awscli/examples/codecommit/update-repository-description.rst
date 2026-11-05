**To change the description for a repository**

The following ``update-repository-description`` example changes the description for an AWS CodeCommit repository. ::

    aws codecommit update-repository-description \
        --repository-name MyDemoRepo \
        --repository-description "This description was changed"

This command produces no output.

For more information, see `Change AWS CodeCommit repository settings <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-change-repository.html>`__ in the *AWS CodeCommit User Guide*.

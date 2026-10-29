**To change the name of a repository**

The following ``update-repository-name`` example changes the name of an AWS CodeCommit repository. Changing the name of the AWS CodeCommit repository will change the SSH and HTTPS URLs that users need to connect to the repository. Users will not be able to connect to this repository until they update their connection settings. Also, because the repository's ARN will change, changing the repository name will invalidate any IAM user policies that rely on this repository's ARN. ::

    aws codecommit update-repository-name \
        --old-name MyDemoRepo \
        --new-name MyRenamedDemoRepo

This command produces no output.

For more information, see `Change AWS CodeCommit repository settings <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-change-repository.html>`__ in the *AWS CodeCommit User Guide*.

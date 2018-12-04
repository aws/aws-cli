**To delete a repository**

This example command force deletes a repository named ``ubuntu`` in the default
registry for an account. The ``--force`` flag is required if the repository
contains images.

Command::

  aws ecr delete-repository --force --repository-name ubuntu

Output::

  {
      "repository": {
          "registryId": "<aws_account_id>",
          "repositoryName": "ubuntu",
          "repositoryArn": "arn:aws:ecr:us-west-2:<aws_account_id>:repository/ubuntu"
      }
  }

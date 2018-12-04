**To create a repository**

This example creates a repository called ``nginx-web-app`` inside the
``project-a`` namespace in the default registry for an account.

Command::

  aws ecr create-repository --repository-name project-a/nginx-web-app

Output::

  {
      "repository": {
          "registryId": "<aws_account_id>",
          "repositoryName": "project-a/nginx-web-app",
          "repositoryArn": "arn:aws:ecr:us-west-2:<aws_account_id>:repository/project-a/nginx-web-app"
      }
  }

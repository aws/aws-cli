**To view a list of pull requests in a repository**

The following ``list-pull-requests`` example lists pull requests created by an IAM user with the ARN ``arn:aws:iam::123456789012:user/Li_Juan`` and the status of ``CLOSED`` in an AWS CodeCommit repository named ``MyDemoRepo``. ::

    aws codecommit list-pull-requests \
        --author-arn arn:aws:iam::123456789012:user/Li_Juan \
        --pull-request-status CLOSED \
        --repository-name MyDemoRepo

Output::

    {
        "nextToken": "",
        "pullRequestIds": ["2","12","16","22","23","35","30","39","47"]
    }

For more information, see `View pull requests in an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-pull-request.html>`__ in the *AWS CodeCommit User Guide*.

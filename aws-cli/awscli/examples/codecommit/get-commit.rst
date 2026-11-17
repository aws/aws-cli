**To view information about a commit in a repository**

The following ``get-commit`` example displays details about a commit with the system-generated ID of ``7e9fd3091thisisanexamplethisisanexample1`` in an AWS CodeCommit repository named ``MyDemoRepo``. ::

    aws codecommit get-commit \
        --repository-name MyDemoRepo \
        --commit-id 7e9fd3091thisisanexamplethisisanexample1

Output::

    {
        "commit": {
            "additionalData": "",
            "committer": {
                "date": "1484167798 -0800",
                "name": "Mary Major",
                "email": "mary_major@example.com"
            },
            "author": {
                "date": "1484167798 -0800",
                "name": "Mary Major",
                "email": "mary_major@example.com"
            },
            "treeId": "347a3408thisisanexampletreeidexample",
            "parents": [
                "7aa87a031thisisanexamplethisisanexample1"
            ],
            "message": "Fix incorrect variable name"
        }
    }

For more information, see `View commit details in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-commit-details.html>`__ in the *AWS CodeCommit User Guide*.

**To view whether there are any merge conflicts for a pull request**

The following ``get-merge-conflicts`` example displays whether there are any merge conflicts between the tip of a source branch named 'my-feature-branch' and a destination branch named 'master' in a repository named 'MyDemoRepo'. ::

    aws codecommit get-merge-conflicts \
        --repository-name MyDemoRepo \
        --source-commit-specifier my-feature-branch \
        --destination-commit-specifier master \
        --merge-option FAST_FORWARD_MERGE

Output::

    {
        "destinationCommitId": "fac04518EXAMPLE",
        "mergeable": false,
        "sourceCommitId": "16d097f03EXAMPLE"
    }

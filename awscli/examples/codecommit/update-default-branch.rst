**To change the default branch for a repository**

The following ``update-default-branch`` example changes the default branch for an AWS CodeCommit repository. This command produces output only if there are errors. ::

    aws codecommit update-default-branch \
        --repository-name MyDemoRepo \
        --default-branch-name MyNewBranch

Output::

    None.
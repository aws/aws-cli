**To change the description for a repository**

The following ``update-repository-description`` example changes the description for an AWS CodeCommit repository. This command produces no output. ::

    aws codecommit update-repository-description \
        --repository-name MyDemoRepo \
        --repository-description "This description was changed"

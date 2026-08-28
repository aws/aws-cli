**To update a run group**

The following ``update-run-group`` example updates the settings of a run group with id ``1234567``. ::

    aws omics update-run-group \
        --id 1234567 \
        --max-cpus 10
        --name "updated-run-name"

For more information, see `Creating run groups <https://docs.aws.amazon.com/omics/latest/dev/creating-run-groups.html>`__ in the *AWS HealthOmics User Guide*.

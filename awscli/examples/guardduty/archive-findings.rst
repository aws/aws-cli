**To archive findings in the current region**

The following ``archive-findings`` example archives findings in the current region. ::

    aws guardduty archive-findings \
        --detector-id 12abc34d567e8fa901bc2d34eexample \
        --finding-ids d6b94fb03a66ff665f7db8764example 3eb970e0de00c16ec14e6910fexample

This command produces no output.

For more information, see `Creating suppression rules in GuardDuty <https://docs.aws.amazon.com/guardduty/latest/ug/create-suppression-rules-guardduty.html>`__ in the *GuardDuty User Guide*.

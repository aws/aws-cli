**To Enable A Control Tower Baseline**

The following ``enable-baseline`` example enables an AWS Control Tower baseline if baseline 'IdentityCenterBaseline' is **not** enabled::

    aws controltower enable-baseline \
        --baseline-identifier arn:aws:controltower:us-east-1::baseline/17BSJV3IGJ2QSGA2 \
        --baseline-version 4.0 \
        --target-identifier arn:aws:organizations::371737006705:ou/o-s64ryihwdd/ou-oq9f-i5wnx6zf

Output::

   {
        "arn": "arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2",
        "operationIdentifier": "51e190ac-8a37-4f6d-b63c-fb5104b5db38"
   }

The following ``enable-baseline`` example enables an AWS Control Tower baseline if baseline 'IdentityCenterBaseline' is enabled::

    aws controltower enable-baseline \
        --baseline-identifier arn:aws:controltower:us-east-1::baseline/17BSJV3IGJ2QSGA2 \
        --baseline-version 4.0 \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryixxxx/ou-oqxx-i5wnxxxx \
        --parameters '[{"key":"IdentityCenterEnabledBaselineArn","value":"arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XAJNZNCBC1I386C7B"}]'

Output::

   {
        "arn": "arn:aws:controltower:us-east-1:123456789012:enabledbaseline/XOM12BEL4YD578CQ2",
        "operationIdentifier": "51e190ac-8a37-4f6d-b63c-fb5104b5db38"
   }

For more information, see `AWS Control Tower Baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.

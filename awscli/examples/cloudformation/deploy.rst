**To deploy a template to a stack**

The following command deploys a template named ``template.json`` to a stack named
``my-new-stack``. ::


    aws cloudformation deploy --template-file /path_to_template/template.json --stack-name my-new-stack --parameter-overrides Key1=Value1 Key2=Value2 --tags Key1=Value1 Key2=Value2

The following command deploys the same template using parameters from the JSON file ``parameters.json``. ::

    aws cloudformation deploy --template-file /path_to_template/template.json --stack-name my-new-stack --parameter-overrides file://path_to_parameters/parameters.json --tags Key1=Value1 Key2=Value2

Supported JSON syntax
~~~~~~~~~~~~~~~~~~~~~

Original format::

    [
        "Key1=Value1",
        "Key2=Value2"
    ]

CloudFormation like format::

    [
        {
            "ParameterKey": "Key1",
            "ParameterValue": "Value1"
        },
        {
            "ParameterKey": "Key2",
            "ParameterValue": "Value2"
        }
    ]

.. note::

    Only ParameterKey and ParameterValue are expected keys, command will throw an exception if receives unexpected keys (e.g. UsePreviousValue or ResolvedValue).

CodePipeline like format::

    [
        "Parameters": {
            "Key1": "Value1",
            "Key2": "Value2"
        }
    ]

Following command deploys template named ``template.json`` to a stack named
``my-new-stack``::

    aws cloudformation deploy --template-file /path_to_template/template.json --stack-name my-new-stack --parameter-overrides Key1=Value1 Key2=Value2 --tags Key1=Value1 Key2=Value2

Following command deploys template named ``template.json`` to a stack named
``my-new-stack``. If an error is encountered, the deploy stops and a rollback is not triggered::

    aws cloudformation deploy --template-file /path_to_template/template.json --stack-name my-new-stack --disable-rollback

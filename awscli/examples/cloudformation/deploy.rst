Following command deploys template named ``template.json`` to a stack named
``my-new-stack``::


    aws cloudformation deploy --template-file /path_to_template/template.json --stack-name my-new-stack --parameter-overrides Key1=Value1 Key2=Value2


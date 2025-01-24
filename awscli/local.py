from awscli.clidriver import create_clidriver

driver = create_clidriver()
command = (
    #sso logout".split()
    #"sso login --profile sso-admin".split()
    #"sso login --profile sso-admin --ca-bundle ~/Downloads/charles-proxy-ssl-proxying-certificate.pem --debug".split()
    #r's3 cp s3://shovlia-test/test214.txt test.txt'.split()
    # r'configure sso'.split()
    #r'stepfunctions create-state-machine-alias --name foobar --routing-configuration stateMachineVersionArn=arn:aws:states:us-east-1:721781603755:stateMachine:MyStateMachine-0ua40qmit:1,weight=1'.split()


)
print(driver.main(command))
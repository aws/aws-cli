all: exe macpkg

exe:
	rm -rf ./dist/aws
	pyinstaller aws.spec && echo "aws exe built"
	pyinstaller aws_completer.spec && echo "aws_completer exe built"
	cp -r dist/aws_completer/* dist/aws/
	rm -rf dist/aws_completer/

macpkg:
	rm -f dist/aws-cli.pkg
	$(eval CLI_VERSION=$(shell dist/aws/aws --version 2>&1 | cut -d' ' -f 1 | cut -d'/' -f 2))
	cd dist && pkgbuild --identifier com.amazon.awscli --root ./aws/ --install-location /usr/local/aws/ --scripts ../scripts/ --version $(CLI_VERSION) aws-cli.pkg
	cd dist && productbuild --distribution distribution.xml --resources ../resources/ "AWS-CLI-Installer.pkg"
	rm dist/aws-cli.pkg
	@echo Mac PKG file is available at dist/AWS-CLI-Installer.pkg

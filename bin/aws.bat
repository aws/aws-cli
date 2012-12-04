@echo off
rem = """

python -x "%~f0" %1 %2 %3 %4 %5 %6 %7 %8 %9
goto endofPython """

# Your python code goes here ..
import awscli.clidriver


def main():
    driver = awscli.clidriver.CLIDriver(provider_name='aws')
    driver.main()


if __name__ == "__main__":
   print "Hello World"

rem = """
:endofPython """

import os
import sys
import json
import re
import argparse
import math
import awscli.clidriver
from awscli.help import PagingHelpRenderer
import pandas as pd
import openpyxl

EXAMPLESDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLESDIR = os.path.join(EXAMPLESDIR, 'awscli','examples')


'''Return the list of all current services name'''
def get_service_names(help_command):

    total_operationslist = []

    # For each AWS service 
    for service_name in help_command.command_table:
        if service_name == 'help':
            continue
     
        service_command = help_command.command_table[service_name]

        service_help_command = service_command.create_help_command()

        if service_help_command is None:
                # Do not document anything that does not have a help command.
                continue
        
        total_operationslist.append(service_name)

    return total_operationslist


'''Returns the example count for a single operation'''
def get_operation_counts(service, operation, suboperation=None):

    if suboperation is None:
        example_file = os.path.join(EXAMPLESDIR, service, f"{operation}.rst")
        example_pattern = f"aws {service} {operation}"
    else:
        example_file = os.path.join(EXAMPLESDIR, service, operation, f"{suboperation}.rst")
        example_pattern = f"aws {service} {operation} {suboperation}"


    # if file exists within directory, find occurrences of aws regex patten for the example count
    if os.path.exists(example_file):

        with open(example_file, "r") as f:

            rst_content = f.read()

        occurrences = re.findall(example_pattern, rst_content)

        return len(occurrences)
    
    # Otherwise there are no current examples for this operation
    return 0


'''Returns a single dictionary of serivce total_operations and their example counts'''
def get_example_counts(less_than, service, help_command):

    service_command = help_command.command_table[service]

    service_help_command = service_command.create_help_command()

    service_counts = {}

    # Populate empty service dictionary
    for operation in service_help_command.command_table:

        if operation == 'help':
                continue

        operation_help_command = service_help_command.command_table[operation]

        subcommand_table = getattr(operation_help_command, 'subcommand_table', {})

        # If there are subtotal_operations, call get_operation_counts on the subcommand
        if (len(subcommand_table) > 0):
            for subcommand_name in subcommand_table:
                operation_counts = get_operation_counts(service, operation, subcommand_name)   
                if operation_counts < less_than:
                    service_counts[operation + '/' + subcommand_name] = operation_counts 
        else:
            operation_counts = get_operation_counts(service, operation)

            if operation_counts < less_than:
                service_counts[operation] = operation_counts

    return service_counts



'''Creates an xlsx output of the json structure if --xlsx is set to true'''
def create_xlsx_output(all_service_total_operations):

    services_excel_sheet = []

    for service in all_service_total_operations.keys():

        service_total_operations = all_service_total_operations[service]

        for command, example_count in service_total_operations.items():
            
            service_sheet_entry = [service, command, example_count]
            services_excel_sheet.append(service_sheet_entry)

    df = pd.DataFrame(services_excel_sheet, columns = ['service', 'command', 'example count'])
    df.to_excel('service_total_operations.xlsx', sheet_name='service_total_operations', index=False)
    
    pass

'''Gets operation to example percentage for the service'''
def get_service_coverage(service_counts, no_coverage):

    operations_covered = 0
    total_operations = 0
            
    for operation in service_counts.keys():

        # Gets the amounts of examples for each operation, adds one to operation covered if > 0.
        if service_counts[operation] > 0:
            operations_covered += 1
        total_operations += 1
            
    coverage_ratio = round(operations_covered/total_operations*100)

    # If --no-coverage flag is True and coverage_ratio for service is 0, add service to dictionary
    if no_coverage == True and coverage_ratio == 0:
        return str(coverage_ratio) + "%"
    
    # If --no-coverage flag is True and coverage_ratio != 0, return None
    elif no_coverage == True and coverage_ratio != 0: 
        empty_string = ""
        return empty_string
    else:
        return str(coverage_ratio) + "%"

        
def main():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--services',
        required=False,
        nargs='*'
    )
    parser.add_argument(
        '--less-than',
        required=False,
        type=int
    )
    parser.add_argument(
        '--xlsx',
        required=False,
        action='store_true'
    )
    parser.add_argument(
        '--service-coverage',
        required=False,
        action='store_true'
    )
    parser.add_argument(
        '--no-coverage',
        required=False,
        action='store_true'
    )
    
    parsed_args = parser.parse_args()
    driver = awscli.clidriver.create_clidriver()
    help_command = driver.create_help_command()

    services = parsed_args.services
    less_than = parsed_args.less_than
    xlsx = parsed_args.xlsx
    service_coverage = parsed_args.service_coverage
    no_coverage = parsed_args.no_coverage

    if not services:
        services = get_service_names(help_command)

    if less_than is None:
        less_than = float('inf')

    
    examples_counts = {}
    service_coverage_dict = {}

    for service in services:

        # returns dictionary of service operations and operation example counts
        service_counts = get_example_counts(less_than, service, help_command)

        # Add service dictionary to examples_counts dictionary
        examples_counts[service] = service_counts
        
        if service_coverage == True:
            # Retrieve service coverage for individual service
            service_percentage = get_service_coverage(service_counts, no_coverage)
            
            if not service_percentage:
                continue
            
            service_coverage_dict[service] = service_percentage

    if xlsx:
        create_xlsx_output(examples_counts)

    if service_coverage == True:
        print(json.dumps(service_coverage_dict, indent =2))
    else:
        print(json.dumps(examples_counts, indent =2))

    


# Main function
if __name__ == '__main__':
    main()



# Instructions
# Export subtasks from OneTrust as CSV.
# Look out for the file dialog.

# Import packages
from InquirerPy import prompt
from simple_salesforce import Salesforce
import numpy as np
import pandas as pd
import datetime
from math import isnan
import os
import tkinter as tk
from tkinter import filedialog
from configparser import ConfigParser
import sys
import traceback

def get_user_action():
    print()
    questions = [
        {
            'type': 'list',
            'name': 'action',
            'message': 'What action would you like to perform?',
            'choices': [
                'Handle a list of requests',
                'Handle a list of email addresses',
                'Delete all flagged records',
                'Exit'
            ]
        }
    ]
    answers = prompt(questions)
    return answers['action']

def main():
    try:
        # Welcome message
        print('Welcome to the contact removal tool.')
        print('Getting things ready...')
        
        # Set working directory
        def get_script_dir():
            """ Get the directory of the current script or executable """
            if getattr(sys, 'frozen', False):
                # If the application is run as a bundle, the pyInstaller bootloader
                # sets the sys.frozen attribute and this method returns the path
                # to the bundle file.
                return os.path.dirname(sys.executable)
            else:
                # If the application is run in a normal Python environment, return
                # the path to the script file.
                return os.path.dirname(os.path.abspath(__file__))

        script_dir = get_script_dir()
        os.chdir(script_dir)

        # Get SFDC credentials
        print('Opening sfdc.ini to get the SFDC credentials.')
        # Initialize the ConfigParser
        config = ConfigParser()

        # Define the path to the config file
        config_file_path = 'sfdc.ini'

        # Check if the config file exists
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"{config_file_path} does not exist.")

        # Read the config.ini file
        config.read(config_file_path)

        # Retrieve the secrets
        SFDC_USERNAME = config.get('secrets', 'SFDC_USERNAME')
        SFDC_PASSWORD = config.get('secrets', 'SFDC_PASSWORD')
        SFDC_TOKEN = config.get('secrets', 'SFDC_TOKEN')

        # Raise an error if any of the secrets are missing
        if not SFDC_USERNAME or not SFDC_PASSWORD or not SFDC_TOKEN:
            raise ValueError("One or more SFDC credentials are not set in config file.")
        
        while True:
            # Get user selection
            user_action = get_user_action()
            
            if user_action == 'Handle a list of requests':
                handle_requests()
            elif user_action == 'Handle a list of email addresses':
                handle_email_list()
            elif user_action == 'Delete all flagged records':
                delete_flagged_records()
            elif user_action == 'Exit':
                print("Exiting...")
                break

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        input("Press Enter to exit...")

def handle_requests():
    print("Handling list of requests...")

    # Load requests
    root = tk.Tk()
    root.withdraw()
    res_2 = input('XLSX (x) or CSV (c)? ')
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()

    # Handle case where no file is selected
    if not file_path:
        print("No file selected. Returning to the main menu...")
        return  # Return to the main menu
    
    try:
        if res_2 == 'x':
            df_requests = pd.read_excel(file_path, dtype=str)
        if res_2 == 'c':
            df_requests = pd.read_csv(file_path, dtype=str)
        else:
            print("Invalid input. Returning to the main menu...")
            return
    except Exception as e:
        print(f"Error loading the file: {e}. Returning to the main menu...")
        return  # Return to the main menu if file reading fails
        
    print(f"{df_requests.shape[0]} requests loaded.")
    
    # Filter for Salesforce tasks
    print('Filtering for Salesforce tasks.')
    df_requests = df_requests.loc[df_requests['Task Assignee - Subtask'] == 'Salesforce'].reset_index(drop=True)
    print(f"{df_requests.shape[0]} requests remaining.")

    
    # Mapping based on conditions
    print('Categorizing.')
    conditions = [
        df_requests['Workflows'].isin(['[Consumer] Data Removal', '[E&E] Data Removal']),
        df_requests['Workflows'] == '[Consumer] Unsubscribe',
        df_requests['Workflows'] == '[Consumer] Credit Card Removal'
    ]

    choices = ['data_removal', 'unsubscribe', 'credit_card_removal']
        
    df_requests['request_type'] = np.select(conditions, choices, default=np.nan)

    # Get lists of email addresses
    print('Extracting email addresses.')
    
    data_removal_email_list = df_requests.loc[df_requests['request_type'] == 'data_removal']['Email'].tolist()
    print(f"Identified {len(data_removal_email_list)} data removal requests.")

    unsubscribe_email_list = df_requests.loc[df_requests['request_type'] == 'unsubscribe']['Email'].tolist()
    print(f"Identified {len(unsubscribe_email_list)} unsubscribe requests.")

    cc_removal_email_list = df_requests.loc[df_requests['request_type'] == 'credit_card_removal']['Email'].tolist()
    print(f"Identified {len(cc_removal_email_list)} credit card removal requests.")

    # To strings for queries
    data_removal_email_list_str = ','.join(f"'{x}'" for x in data_removal_email_list)
    unsubscribe_email_list_str = ','.join(f"'{x}'" for x in unsubscribe_email_list)
    cc_removal_email_list_str = ','.join(f"'{x}'" for x in cc_removal_email_list)

    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME,
        password=SFDC_PASSWORD,
        security_token=SFDC_TOKEN
    )
    
    # Query data removal contacts and accounts
    # Careful: data mix
    
    print('Querying accounts and contacts from SFDC.')
    query = """
    SELECT
        Id,
        AccountId,
        Account.RecordTypeId
    FROM Contact WHERE Email IN (
        {0}
    )
    """

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Add variables
    query = query.format(data_removal_email_list_str)
    # Run query
    data = sf.query_all(query)

    # Get rows
    rows = []
    for item in data['records']:
        row = {}
        try:
            row['Id'] = item['Id']
            row['AccountId'] = item['AccountId']
        except:
            pass
        try:
            row['RecordTypeId'] = item['Account']['RecordTypeId']
        except:
            pass
        rows.append(row)

    # To dataframe
    df = pd.DataFrame(rows)
    print(f"{df.shape[0]} contact(s) found.")

    # Set flags
    # For contacts
    df['GDPR__c'] = 1
    
    print(f"Identified {df.shape[0]} contact(s) to be flagged for deletion. (Setting `GDPR__c` to true.)")
    
    # For accounts
    df['GDPR_Account__c'] = np.where(df['RecordTypeId'] == '012d0000000W68QAAS', 1, 0)
    print(f"Identified {df['GDPR_Account__c'].sum()} household account(s) to be flagged for deletion. (Setting `GDPR_Account__c` to true.)")
    
    # Split
    df_contacts = df[[
        'Id',
        'GDPR__c'
    ]]

    df_accounts = df[[
        'AccountId',
        'GDPR_Account__c'
    ]]

    # Rename
    df_accounts = df_accounts.rename(columns={'AccountId': 'Id'}, inplace=False)
    # Filter
    df_accounts = df_accounts.loc[df_accounts['GDPR_Account__c'] == 1]

    
    # Export
    print('Exporting to CSV.')
    os.makedirs('exports', exist_ok=True)
    df_contacts.to_csv(r'exports/data_removal_contacts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)
    df_accounts.to_csv(r'exports/data_removal_accounts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)

    # Convert to lists of dicts
    target_data_contacts = df_contacts.to_dict('records')
    target_data_accounts = df_accounts.to_dict('records')

    # Push contact updates to SFDC
    print('Pushing the GDPR flag update to contacts in SFDC. Please wait.')
    result = sf.bulk.Contact.update(target_data_contacts,batch_size=20,use_serial=True)

    # Print success count
    success_list = [1 if d['success'] is True else 0 for d in result]
    success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
    print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)

    # Write results to file
    print('Exporting the results.')
    os.makedirs('results', exist_ok=True)
    with open(r'results/results_data_removal_contacts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
        for item in result:
            f.write("%s\n" % item)

    # Push account updates to SFDC
    print('Pushing the GDPR flag update to household accounts in SFDC. Please wait.')
    result = sf.bulk.Account.update(target_data_accounts,batch_size=20,use_serial=True)

    # Print success count
    success_list = [1 if d['success'] is True else 0 for d in result]
    success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
    print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)

    # Write results to file
    print('Exporting the results.')
    os.makedirs('results', exist_ok=True)
    with open(r'results/results_data_removal_accounts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
        for item in result:
            f.write("%s\n" % item)
    
    # Process unsubscribe contacts
    if len(unsubscribe_email_list) > 0:

        # Query unsubscribe contacts
        print('Querying contacts from SFDC that want to unsubscribe.')
        query = """
        SELECT
            Id
        FROM Contact WHERE Email IN (
            {0}
        )
        """

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(unsubscribe_email_list_str)
        # Run query
        data = sf.query_all(query)

        
        # To dataframe
        df = pd.DataFrame(data['records']).drop(['attributes'],axis=1)
        print(f"{df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:
            
            # Set flags
            print("Preparing to set `HasOptedOutOfEmail` to true and `Marketing_Status__c` to 'No Marketing'.")
            df['HasOptedOutOfEmail'] = 1
            # df['Explicit_Opt_in__c'] = 0
            # df['Opt_in__c'] = 0
            df['Marketing_Status__c'] = 'No Marketing'
            df.shape

            # Export
            print('Exporting to CSV.')
            os.makedirs('exports', exist_ok=True)
            df.to_csv(r'exports/unsubscribe_contacts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)

            # Convert to list of dicts
            target_data = df.to_dict('records')

            # Push contact updates to SFDC
            print('Pushing the unsubscribe updates to contacts in SFDC. Please wait.')
            result = sf.bulk.Contact.update(target_data,batch_size=500,use_serial=True)

            # Print success count
            success_list = [1 if d['success'] is True else 0 for d in result]
            success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
            print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)

            # Write results to file
            print('Exporting the results.')
            os.makedirs('results', exist_ok=True)
            with open(r'results/results_unsubscribe_contacts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
                for item in result:
                    f.write("%s\n" % item)
        else:
            pass

    else:
        print('No unsubscribe requests to process.')
 
    # Process credit card removal requests
    if len(cc_removal_email_list) > 0:
    
        # Filter credit card removal requests
        df_cc = df_requests[df_requests.request_type == 'credit_card_removal'].reset_index(drop=True)
        df_cc.shape
        
        # Query credit card removal contacts
        print('Querying credit card removal contacts from SFDC.')
        query = """
        SELECT
            Id,
            Email,
            AccountId,
            Account.RecordTypeId
        FROM Contact WHERE Email IN (
            {0}
        )
        """

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(cc_removal_email_list_str)
        # Run query
        data = sf.query_all(query)

        # Get rows
        rows = []
        for item in data['records']:
            row = {}
            try:
                row['Id'] = item['Id']
                row['AccountId'] = item['AccountId']
                row['Email'] = item['Email']
            except:
                pass
            try:
                row['RecordTypeId'] = item['Account']['RecordTypeId']
            except:
                pass
            rows.append(row)

        # To dataframe
        df = pd.DataFrame(rows)
        print(f"{df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:

            # Add URLs
            print('Generating SFDC links.')
            df['sfdc_contact_link'] = 'https://rs.lightning.force.com/lightning/r/' + df['Id'] + '/view'

            # Change email addresses to lowercase
            df['Email'] = df['Email'].str.lower()
            df_cc['Email'] = df_cc['Email'].str.lower()

            # Merge
            df_cc_final = df_cc.merge(df, on='Email', how='left')

            # Export
            print('Exporting to CSV.')
            os.makedirs('exports', exist_ok=True)
            df_cc_final.to_csv(r'exports/cc_removal_requests_with_contacts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)

            # Reminder
            print("Don't forget to open the exported credit card removal requests file and manually look for credit card numbers in SFDC.")

    else:
        print('No credit card removal requests to process.')

    input("Task completed. 🚀 Press Enter to return to the main menu...")

def handle_email_list():
    print("Handling list of email addresses...")

    # Get lists of email addresses
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    
    # Handle case where no file is selected
    if not file_path:
        print("No file selected. Returning to the main menu...")
        return  # Return to the main menu
    
    try:
        with open(file_path) as f:
            lines = f.readlines()
            contacts = [line.rstrip() for line in lines]
    except Exception as e:
        print(f"Error loading the file: {e}. Returning to the main menu...")
        return  # Return to the main menu if file reading fails
    
    # Split into chunks of length n
    n = 400
    contacts_chunks = [contacts[i:i + n] for i in range(0, len(contacts), n)]
    total_chunks = len(contacts_chunks)
    
    print(f"{len(contacts)} email addresses loaded.")
    print(f'Splitting the data into {total_chunks} chunks of up to 400 contacts each.')

    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME,
        password=SFDC_PASSWORD,
        security_token=SFDC_TOKEN
    )

    # Execute
    for chunk_index, chunk in enumerate(contacts_chunks, start=1):
        
        # Escape apostrophes in email addresses
        chunk = [email.replace("'", "\\'") for email in chunk]

        # To strings for query
        print(f'Starting chunk {chunk_index} of {total_chunks}.')
        contacts_str = ','.join(f"'{x}'" for x in chunk)

        # Query data removal contacts
        print('Querying contacts from SFDC.')
        query = """
        SELECT
            Id,
            AccountId,
            Account.RecordTypeId
        FROM Contact WHERE Email IN (
            {0}
        )
        """

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(contacts_str)
        # Run query
        data = sf.query_all(query)

        if not data['records']:
            print("No contacts found for this chunk.")
        
        else:
            
            # Get rows
            rows = []
            for item in data['records']:
                row = {}
                try:
                    row['Id'] = item['Id']
                    row['AccountId'] = item['AccountId']
                except:
                    pass
                try:
                    row['RecordTypeId'] = item['Account']['RecordTypeId']
                except:
                    pass
                rows.append(row)

            # To dataframe
            df = pd.DataFrame(rows)
            print(f"Identified {df.shape[0]} contact(s) to be flagged for deletion. (Setting `GDPR__c` to true.)")

            # Check if data was found
            if df.shape[0] > 0:
                # Process contacts
                df['GDPR__c'] = 1
                df_contacts = df[[
                    'Id',
                    'GDPR__c'
                ]]

                # Export
                print('Exporting to CSV.')
                df_contacts.to_csv(r'exports/flag_contacts_from_bulk_list_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)
                # Convert to lists of dicts
                target_data_contacts = df_contacts.to_dict('records')
        
                try:
                    # Push contact updates to SFDC
                    print('Pushing the GDPR flag update to contacts in SFDC. Please wait.')
                    result = sf.bulk.Contact.update(target_data_contacts,batch_size=500,use_serial=True)
                    # Print success count
                    success_list = [1 if d['success'] is True else 0 for d in result]
                    success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
                    
                    print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)
                    # Write result to file
                    
                    print('Exporting the results.')
                    os.makedirs('results', exist_ok=True)
                    with open(r'results/results_flag_contacts_from_bulk_list_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
                        for item in result:
                            f.write("%s\n" % item)
                except:
                    print('Contact update error.')

                # Process accounts
                df['GDPR_Account__c'] = np.where(df['RecordTypeId'] == '012d0000000W68QAAS', 1, 0)
                print(f"Identified {df['GDPR_Account__c'].sum()} household account(s) to be flagged for deletion. (Setting `GDPR_Account__c` to true.)")

                if df['GDPR_Account__c'].sum() > 0:

                    # Drop columns
                    df_accounts = df[[
                        'AccountId',
                        'GDPR_Account__c'
                    ]]
                    # Rename
                    df_accounts = df_accounts.rename(columns={'AccountId': 'Id'}, inplace=False)
                    # Filter
                    df_accounts = df_accounts.loc[df_accounts['GDPR_Account__c'] == 1]
                    # Export
                    print('Exporting to CSV.')
                    df_accounts.to_csv(r'exports/flag_accounts_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)
                    # Convert to lists of dicts
                    target_data_accounts = df_accounts.to_dict('records')
        
                    
                    # Push account updates to SFDC
                    print('Pushing the GDPR flag update to household accounts in SFDC. Please wait.')
                    try:
                        result = sf.bulk.Account.update(target_data_accounts,batch_size=500,use_serial=True)
                        # Print success count
                        success_list = [1 if d['success'] is True else 0 for d in result]
                        success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
                        print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)
                        # Write result to file
                        print('Exporting the results.')
                        with open(r'results/results_flag_accounts_from_bulk_list_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
                            for item in result:
                                f.write("%s\n" % item)
                    except:
                        print('Account update error.')

    input("Task completed. 🚀 Press Enter to return to the main menu...")

def delete_flagged_records():
    print("Deleting all flagged records...")
    
    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME,
        password=SFDC_PASSWORD,
        security_token=SFDC_TOKEN
    )

    # Query cases    
    print('Querying all cases related to contacts flagged for deletion.')
    query = """
    SELECT
        Id
    FROM CASE WHERE Contact.GDPR__c = true
    """

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Run query
    data = sf.query_all(query)

    # To dataframe
    df = pd.DataFrame(data['records']).drop(['attributes'],axis=1)
    print(f"{df.shape[0]} case(s) found.")

    # Export
    print('Exporting to CSV.')
    os.makedirs('exports', exist_ok=True)
    df.to_csv(r'exports/gdpr_contact_cases_to_delete_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)

    # Convert to lists of dicts
    target_data_cases = df.to_dict('records')

    # Push to SFDC
    print('Deleting the cases in SFDC. Please wait.')
    result = sf.bulk.Case.delete(target_data_cases,batch_size=500,use_serial=True)

    # Print success count
    success_list = [1 if d['success'] is True else 0 for d in result]
    success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
    print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)

    # Write result to file
    print('Exporting the results.')
    os.makedirs('results', exist_ok=True)
    with open(r'results/results_gdpr_contact_cases_to_delete_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
        for item in result:
            f.write("%s\n" % item)

    # Query contacts
    print('Querying all contacts flagged for deletion.')
    query = """
    SELECT
        Id
    FROM Contact WHERE GDPR__c = true
    """

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Run query
    data = sf.query_all(query)

    # To dataframe
    df = pd.DataFrame(data['records']).drop(['attributes'],axis=1)
    print(f"{df.shape[0]} contact(s) found.")

    # Export
    print('Exporting to CSV.')
    os.makedirs('exports', exist_ok=True)
    df.to_csv(r'exports/gdpr_contacts_to_delete_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.csv', encoding='utf-8', index=False)

    # Convert to lists of dicts
    target_data_contacts = df.to_dict('records')

    # Push to SFDC
    print('Deleting the contacts in SFDC. Please wait.')
    result = sf.bulk.Contact.delete(target_data_contacts,batch_size=500,use_serial=True)

    # Print success count
    success_list = [1 if d['success'] is True else 0 for d in result]
    success_emoji = '✔️' if (len(success_list) - sum(success_list)) == 0 else '💥'
    print("OK: " + str(sum(success_list)) + ", Fail: " + str(len(success_list) - sum(success_list)) + '. ' + success_emoji)

    # Write result to file
    print('Exporting the results.')
    os.makedirs('results', exist_ok=True)
    with open(r'results/results_gdpr_contacts_to_delete_' + datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.txt', 'w') as f:
        for item in result:
            f.write("%s\n" % item)

    input("Task completed. 🚀 Press Enter to return to the main menu...")

if __name__ == '__main__':
    main()

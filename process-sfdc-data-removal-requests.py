# Instructions
# Export subtasks from OneTrust (legacy) or GURPS (new) as CSV/XLSX.
# You will be prompted to choose the source format.
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
import codecs
import threading
import time
import itertools


# Source format configurations.
# - OneTrust (legacy): column names from the original OneTrust subtask export.
# - GURPS (new): column names from the GURPS subtask export.
SOURCE_FORMATS = {
    "onetrust": {
        "label": "OneTrust (legacy)",
        "dtypes": {
            "Email": str,
            "Workflow": str,
            "Task Assignee - Subtask": str,
            "Request Ref ID": str,
            "Task Name - Subtask": str,
            "Stage": str,
            "Subtask Status - Subtask": str,
            "Task Required - Subtask": str,
            "Task Due Date - Subtask": str,
            "Task Reminder Date - Subtask": str,
            "Task Assigned Date - Subtask": str,
            "First Name": str,
            "Last Name": str,
            "Request Type": str,
            "Due Date": str,
            "Approver": str,
            "Date Submitted": str,
            "Organization": str,
            "Task Resolution - Subtask": str,
            "Subtask Created Stage - Subtask": str,
            "Current Request Stage - Subtask": str,
        },
        "assignee_col": "Task Assignee - Subtask",
        "request_type_col": "Workflow",
        "email_col": "Email",
        "data_removal_values": ["[Consumer] Data Removal", "[E&E] Data Removal"],
        "unsubscribe_values": ["[Consumer] Unsubscribe"],
        "credit_card_values": ["[Consumer] Credit Card Removal"],
    },
    "gurps": {
        "label": "GURPS (new)",
        "dtypes": {
            "Subtask ID": str,
            "Request ID": str,
            "Title": str,
            "Subtask Status": str,
            "Assignee": str,
            "Author": str,
            "Date Created": str,
            "Days Remaining": str,
            "Stage": str,
            "Description": str,
            "Customer Email": str,
            "Request Type": str,
            "Requester Role": str,
            "Request Status": str,
            "Request Due Date": str,
        },
        "assignee_col": "Assignee",
        "request_type_col": "Request Type",
        "email_col": "Customer Email",
        "data_removal_values": ["Data Deletion", "Ee Data Deletion"],
        "unsubscribe_values": ["Unsubscribe"],
        "credit_card_values": ["Credit Card Removal"],
    },
}


def get_user_action():
    print()
    questions = [
        {
            "type": "list",
            "name": "action",
            "message": "What action would you like to perform?",
            "choices": [
                "Process a list of removal requests",
                "Process a list of email addresses",
                "Delete all flagged records in SFDC",
                "Exit",
            ],
        }
    ]
    answers = prompt(questions)
    return answers["action"]


def get_source_format():
    print()
    questions = [
        {
            "type": "list",
            "name": "format",
            "message": "Which source format is the file in?",
            "choices": [
                {"name": SOURCE_FORMATS["onetrust"]["label"], "value": "onetrust"},
                {"name": SOURCE_FORMATS["gurps"]["label"], "value": "gurps"},
            ],
        }
    ]
    answers = prompt(questions)
    return answers["format"]


def main():
    try:
        # Add these lines at the start of main() to ensure proper encoding
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)

        # ASCII art
        print(
            """🚀
####### **********   *************      
#######   ********* **************      
#######    ***********************      
#######      ************ ********      
#######    ***********************      
#######   ******** *********************    
####### *********    *******************
"""
        )
        # Welcome message
        print("Welcome to the contact removal tool.")
        print("Getting things ready...")

        # Set working directory
        def get_script_dir():
            """Get the directory of the current script or executable"""
            if getattr(sys, "frozen", False):
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
        print("Opening sfdc.ini to get the SFDC credentials.")
        # Initialize the ConfigParser
        config = ConfigParser()

        # Define the path to the config file
        config_file_path = "sfdc.ini"

        # Check if the config file exists
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"{config_file_path} does not exist.")

        # Read the config.ini file
        config.read(config_file_path)

        # Retrieve the secrets
        SFDC_USERNAME = config.get("secrets", "SFDC_USERNAME")
        SFDC_PASSWORD = config.get("secrets", "SFDC_PASSWORD")
        SFDC_TOKEN = config.get("secrets", "SFDC_TOKEN")

        # Raise an error if any of the secrets are missing
        if not SFDC_USERNAME or not SFDC_PASSWORD or not SFDC_TOKEN:
            raise ValueError("One or more SFDC credentials are not set in config file.")

        while True:
            # Get user selection
            user_action = get_user_action()

            if user_action == "Process a list of removal requests":
                handle_requests(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Process a list of email addresses":
                handle_email_list(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Delete all flagged records in SFDC":
                delete_flagged_records(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Exit":
                print("Exiting...")
                break

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        input("Press Enter to exit...")


def find_column_case_insensitive(df, target_column):
    """
    Find a column name in the DataFrame using case-insensitive matching.
    Returns the actual column name if found, otherwise returns None.
    """
    target_lower = target_column.lower()
    for col in df.columns:
        if col.lower() == target_lower:
            return col
    return None


def open_file_dialog_focused():
    """
    Opens a file dialog with proper focus handling to prevent it from opening behind other windows.
    Returns the selected file path or empty string if no file is selected.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Keep on top
    root.lift()  # Bring to front
    root.focus_force()  # Force focus
    file_path = filedialog.askopenfilename(parent=root)
    root.destroy()  # Clean up
    return file_path


def handle_requests(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    # Choose source format
    source_key = get_source_format()
    source_config = SOURCE_FORMATS[source_key]
    print(f"Starting to process a list of {source_config['label']} requests...")

    # Load requests
    res_2 = input("XLSX (x) or CSV (c)? ")
    file_path = open_file_dialog_focused()

    # Handle case where no file is selected
    if not file_path:
        print("No file selected. Returning to the main menu...")
        return

    try:
        # First load without dtype to get the actual column names
        if res_2 == "x":
            df_temp = pd.read_excel(file_path, nrows=0)  # Just get headers
        elif res_2 == "c":
            df_temp = pd.read_csv(file_path, nrows=0)  # Just get headers
        else:
            print("Invalid input. Returning to the main menu...")
            return

        # Map desired column names (per source format) to actual column names
        dtype_dict = {}
        for desired_col, dtype in source_config["dtypes"].items():
            actual_col = find_column_case_insensitive(df_temp, desired_col)
            if actual_col:
                dtype_dict[actual_col] = dtype

        # Now load the full file with proper dtypes
        if res_2 == "x":
            df_requests = pd.read_excel(file_path, dtype=dtype_dict)
        elif res_2 == "c":
            df_requests = pd.read_csv(file_path, dtype=dtype_dict)

    except Exception as e:
        print(f"Error loading the file: {e}. Returning to the main menu...")
        return

    print(f"{df_requests.shape[0]} requests loaded.")

    # Find column names case-insensitively (using the names for the chosen format)
    task_assignee_col = find_column_case_insensitive(
        df_requests, source_config["assignee_col"]
    )
    request_type_col = find_column_case_insensitive(
        df_requests, source_config["request_type_col"]
    )
    email_col = find_column_case_insensitive(df_requests, source_config["email_col"])

    if not task_assignee_col:
        print(
            f"Error: Could not find '{source_config['assignee_col']}' column (case-insensitive). Available columns:"
        )
        print(list(df_requests.columns))
        return

    if not request_type_col:
        print(
            f"Error: Could not find '{source_config['request_type_col']}' column (case-insensitive). Available columns:"
        )
        print(list(df_requests.columns))
        return

    if not email_col:
        print(
            f"Error: Could not find '{source_config['email_col']}' column (case-insensitive). Available columns:"
        )
        print(list(df_requests.columns))
        return

    # Filter for Salesforce tasks
    print("Filtering for Salesforce tasks.")
    df_requests = df_requests.loc[
        df_requests[task_assignee_col] == "Salesforce"
    ].reset_index(drop=True)
    print(f"{df_requests.shape[0]} requests remaining.")

    # Mapping based on conditions (per source format)
    print("Categorizing.")
    conditions = [
        df_requests[request_type_col].isin(source_config["data_removal_values"]),
        df_requests[request_type_col].isin(source_config["unsubscribe_values"]),
        df_requests[request_type_col].isin(source_config["credit_card_values"]),
    ]

    choices = ["data_removal", "unsubscribe", "credit_card_removal"]

    df_requests["request_type"] = np.select(conditions, choices, default="unknown")

    # If you need to identify unmatched records later, you can do:
    unmatched_requests = df_requests[df_requests["request_type"] == "unknown"]

    # Get lists of email addresses
    print("Extracting email addresses.")

    data_removal_email_list = df_requests.loc[
        df_requests["request_type"] == "data_removal"
    ][email_col].tolist()
    print(f"Identified {len(data_removal_email_list)} data removal requests.")

    unsubscribe_email_list = df_requests.loc[
        df_requests["request_type"] == "unsubscribe"
    ][email_col].tolist()
    print(f"Identified {len(unsubscribe_email_list)} unsubscribe requests.")

    cc_removal_email_list = df_requests.loc[
        df_requests["request_type"] == "credit_card_removal"
    ][email_col].tolist()
    print(f"Identified {len(cc_removal_email_list)} credit card removal requests.")

    # Escape apostrophes in email addresses for SOQL
    data_removal_email_list = [e.replace("'", "\\'") for e in data_removal_email_list]
    unsubscribe_email_list = [e.replace("'", "\\'") for e in unsubscribe_email_list]
    cc_removal_email_list = [e.replace("'", "\\'") for e in cc_removal_email_list]

    # To strings for queries
    data_removal_email_list_str = ",".join(f"'{x}'" for x in data_removal_email_list)
    unsubscribe_email_list_str = ",".join(f"'{x}'" for x in unsubscribe_email_list)
    cc_removal_email_list_str = ",".join(f"'{x}'" for x in cc_removal_email_list)

    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME, password=SFDC_PASSWORD, security_token=SFDC_TOKEN
    )

    # Query data removal contacts and accounts
    # Careful: data mix

    query = """
    SELECT
        Id,
        AccountId,
        Account.RecordTypeId
    FROM Contact WHERE Email IN (
        {0}
    )
    """

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print("Querying accounts and contacts from SFDC...", end="", flush=True)
    spinner_thread.start()

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Add variables
    query = query.format(data_removal_email_list_str)
    # Run query
    data = sf.query_all(query)

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # Get rows
    rows = []
    for item in data["records"]:
        row = {}
        try:
            row["Id"] = item["Id"]
            row["AccountId"] = item["AccountId"]
        except:
            pass
        try:
            row["RecordTypeId"] = item["Account"]["RecordTypeId"]
        except:
            pass
        rows.append(row)

    # To dataframe
    df = pd.DataFrame(rows)
    print(f"{df.shape[0]} contact(s) found.")

    # Set flags
    # For contacts
    df["GDPR__c"] = 1

    print(
        f"Identified {df.shape[0]} contact(s) to be flagged for deletion. (Setting `GDPR__c` to true.)"
    )

    # For accounts
    df["GDPR_Account__c"] = np.where(df["RecordTypeId"] == "012d0000000W68QAAS", 1, 0)
    print(
        f"Identified {df['GDPR_Account__c'].sum()} household account(s) to be flagged for deletion. (Setting `GDPR_Account__c` to true.)"
    )

    # Split
    df_contacts = df[["Id", "GDPR__c"]]

    df_accounts = df[["AccountId", "GDPR_Account__c"]]

    # Rename
    df_accounts = df_accounts.rename(columns={"AccountId": "Id"}, inplace=False)
    # Filter
    df_accounts = df_accounts.loc[df_accounts["GDPR_Account__c"] == 1]

    # Export
    print("Exporting to CSV.")
    os.makedirs("exports", exist_ok=True)
    df_contacts.to_csv(
        r"exports/data_removal_contacts_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".csv",
        encoding="utf-8",
        index=False,
    )
    df_accounts.to_csv(
        r"exports/data_removal_accounts_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".csv",
        encoding="utf-8",
        index=False,
    )

    # Convert to lists of dicts
    target_data_contacts = df_contacts.to_dict("records")
    target_data_accounts = df_accounts.to_dict("records")

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print("Pushing the GDPR flag update to contacts in SFDC...", end="", flush=True)
    spinner_thread.start()

    # Push contact updates to SFDC
    result = sf.bulk.Contact.update(
        target_data_contacts, batch_size=20, use_serial=True
    )

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # Print success count
    success_list = [1 if d["success"] is True else 0 for d in result]
    success_emoji = "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
    print(
        "OK: "
        + str(sum(success_list))
        + ", Fail: "
        + str(len(success_list) - sum(success_list))
        + ". "
        + success_emoji
    )

    # Write results to file
    print("Exporting the results.")
    os.makedirs("results", exist_ok=True)
    with open(
        r"results/results_data_removal_contacts_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".txt",
        "w",
    ) as f:
        for item in result:
            f.write("%s\n" % item)

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print(
        "Pushing the GDPR flag update to household accounts in SFDC...",
        end="",
        flush=True,
    )
    spinner_thread.start()

    # Push account updates to SFDC
    result = sf.bulk.Account.update(
        target_data_accounts, batch_size=20, use_serial=True
    )

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # Print success count
    success_list = [1 if d["success"] is True else 0 for d in result]
    success_emoji = "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
    print(
        "OK: "
        + str(sum(success_list))
        + ", Fail: "
        + str(len(success_list) - sum(success_list))
        + ". "
        + success_emoji
    )

    # Write results to file
    print("Exporting the results.")
    os.makedirs("results", exist_ok=True)
    with open(
        r"results/results_data_removal_accounts_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".txt",
        "w",
    ) as f:
        for item in result:
            f.write("%s\n" % item)

    # Process unsubscribe contacts
    if len(unsubscribe_email_list) > 0:

        # Query unsubscribe contacts
        query = """
        SELECT
            Id
        FROM Contact WHERE Email IN (
            {0}
        )
        """

        # Start spinner
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

        print(
            "Querying contacts that want to unsubscribe from SFDC...",
            end="",
            flush=True,
        )
        spinner_thread.start()

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(unsubscribe_email_list_str)
        # Run query
        data = sf.query_all(query)

        # Stop spinner
        stop_spinner.set()
        spinner_thread.join()
        print("\nDone!")

        # To dataframe
        df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
        print(f"{df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:

            # Set flags
            print(
                "Preparing to set `HasOptedOutOfEmail` to true and `Marketing_Status__c` to 'No Marketing'."
            )
            df["HasOptedOutOfEmail"] = 1
            # df['Explicit_Opt_in__c'] = 0
            # df['Opt_in__c'] = 0
            df["Marketing_Status__c"] = "No Marketing"
            df.shape

            # Export
            print("Exporting to CSV.")
            os.makedirs("exports", exist_ok=True)
            df.to_csv(
                r"exports/unsubscribe_contacts_"
                + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                + ".csv",
                encoding="utf-8",
                index=False,
            )

            # Convert to list of dicts
            target_data = df.to_dict("records")

            # Start spinner
            stop_spinner = threading.Event()
            spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

            print(
                "Pushing the unsubscribe updates to contacts in SFDC...",
                end="",
                flush=True,
            )
            spinner_thread.start()

            # Push contact updates to SFDC
            result = sf.bulk.Contact.update(
                target_data, batch_size=500, use_serial=True
            )

            # Stop spinner
            stop_spinner.set()
            spinner_thread.join()
            print("\nDone!")

            # Print success count
            success_list = [1 if d["success"] is True else 0 for d in result]
            success_emoji = (
                "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
            )
            print(
                "OK: "
                + str(sum(success_list))
                + ", Fail: "
                + str(len(success_list) - sum(success_list))
                + ". "
                + success_emoji
            )

            # Write results to file
            print("Exporting the results.")
            os.makedirs("results", exist_ok=True)
            with open(
                r"results/results_unsubscribe_contacts_"
                + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                + ".txt",
                "w",
            ) as f:
                for item in result:
                    f.write("%s\n" % item)
        else:
            pass

    else:
        print("No unsubscribe requests to process.")

    # Process credit card removal requests
    if len(cc_removal_email_list) > 0:

        # Filter credit card removal requests
        df_cc = df_requests[
            df_requests.request_type == "credit_card_removal"
        ].reset_index(drop=True)
        df_cc.shape

        # Query credit card removal contacts
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

        # Start spinner
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

        print("Querying credit card removal contacts from SFDC...", end="", flush=True)
        spinner_thread.start()

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(cc_removal_email_list_str)
        # Run query
        data = sf.query_all(query)

        # Stop spinner
        stop_spinner.set()
        spinner_thread.join()
        print("\nDone!")

        # Get rows
        rows = []
        for item in data["records"]:
            row = {}
            try:
                row["Id"] = item["Id"]
                row["AccountId"] = item["AccountId"]
                row["Email"] = item["Email"]
            except:
                pass
            try:
                row["RecordTypeId"] = item["Account"]["RecordTypeId"]
            except:
                pass
            rows.append(row)

        # To dataframe
        df = pd.DataFrame(rows)
        print(f"{df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:

            # Add URLs
            print("Generating SFDC links.")
            df["sfdc_contact_link"] = (
                "https://rs.lightning.force.com/lightning/r/" + df["Id"] + "/view"
            )

            # Change email addresses to lowercase
            df["Email"] = df["Email"].str.lower()
            df_cc[email_col] = df_cc[email_col].str.lower()

            # Merge
            df_cc_final = df_cc.merge(
                df, left_on=email_col, right_on="Email", how="left"
            )

            # Export
            print("Exporting to CSV.")
            os.makedirs("exports", exist_ok=True)
            df_cc_final.to_csv(
                r"exports/cc_removal_requests_with_contacts_"
                + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                + ".csv",
                encoding="utf-8",
                index=False,
            )

            # Reminder
            print(
                "Don't forget to open the exported credit card removal requests file and manually look for credit card numbers in SFDC."
            )

    else:
        print("No credit card removal requests to process.")

    input("Task completed. 🚀 Press Enter to return to the main menu...")


def handle_email_list(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    print("Starting to process a list of email addresses...")

    # Get lists of email addresses
    file_path = open_file_dialog_focused()

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
    n = 300
    contacts_chunks = [contacts[i : i + n] for i in range(0, len(contacts), n)]
    total_chunks = len(contacts_chunks)

    print(f"{len(contacts)} email addresses loaded.")
    print(f"Splitting the data into {total_chunks} chunks of up to 300 contacts each.")

    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME, password=SFDC_PASSWORD, security_token=SFDC_TOKEN
    )

    # Execute
    for chunk_index, chunk in enumerate(contacts_chunks, start=1):

        # Escape apostrophes in email addresses
        chunk = [email.replace("'", "\\'") for email in chunk]

        # To strings for query
        print(f"Starting chunk {chunk_index} of {total_chunks}.")
        contacts_str = ",".join(f"'{x}'" for x in chunk)

        # Query data removal contacts
        query = """
        SELECT
            Id,
            AccountId,
            Account.RecordTypeId
        FROM Contact WHERE Email IN (
            {0}
        )
        """

        # Start spinner
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

        print("Querying contacts from SFDC...", end="", flush=True)
        spinner_thread.start()

        # Remove first and last line
        query = "\n".join(query.split("\n")[1:-1])
        # Add variables
        query = query.format(contacts_str)
        # Run query
        data = sf.query_all(query)

        # Stop spinner
        stop_spinner.set()
        spinner_thread.join()
        print("\nDone!")

        if not data["records"]:
            print("No contacts found for this chunk.")

        else:

            # Get rows
            rows = []
            for item in data["records"]:
                row = {}
                try:
                    row["Id"] = item["Id"]
                    row["AccountId"] = item["AccountId"]
                except:
                    pass
                try:
                    row["RecordTypeId"] = item["Account"]["RecordTypeId"]
                except:
                    pass
                rows.append(row)

            # To dataframe
            df = pd.DataFrame(rows)
            print(
                f"Identified {df.shape[0]} contact(s) to be flagged for deletion. (Setting `GDPR__c` to true.)"
            )

            # Check if data was found
            if df.shape[0] > 0:
                # Process contacts
                df["GDPR__c"] = 1
                df_contacts = df[["Id", "GDPR__c"]]

                # Export
                print("Exporting to CSV.")
                df_contacts.to_csv(
                    r"exports/flag_contacts_from_bulk_list_"
                    + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                    + ".csv",
                    encoding="utf-8",
                    index=False,
                )
                # Convert to lists of dicts
                target_data_contacts = df_contacts.to_dict("records")

                try:
                    # Start spinner
                    stop_spinner = threading.Event()
                    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

                    print(
                        "Pushing the GDPR flag update to contacts in SFDC...",
                        end="",
                        flush=True,
                    )
                    spinner_thread.start()

                    # Push contact updates to SFDC
                    result = sf.bulk.Contact.update(
                        target_data_contacts, batch_size=500, use_serial=True
                    )

                    # Stop spinner
                    stop_spinner.set()
                    spinner_thread.join()
                    print("\nDone!")

                    # Print success count
                    success_list = [1 if d["success"] is True else 0 for d in result]
                    success_emoji = (
                        "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
                    )

                    print(
                        "OK: "
                        + str(sum(success_list))
                        + ", Fail: "
                        + str(len(success_list) - sum(success_list))
                        + ". "
                        + success_emoji
                    )
                    # Write result to file

                    print("Exporting the results.")
                    os.makedirs("results", exist_ok=True)
                    with open(
                        r"results/results_flag_contacts_from_bulk_list_"
                        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                        + ".txt",
                        "w",
                    ) as f:
                        for item in result:
                            f.write("%s\n" % item)
                except:
                    # Stop spinner
                    stop_spinner.set()
                    spinner_thread.join()
                    print("\nContact update error.")

                # Process accounts
                df["GDPR_Account__c"] = np.where(
                    df["RecordTypeId"] == "012d0000000W68QAAS", 1, 0
                )
                print(
                    f"Identified {df['GDPR_Account__c'].sum()} household account(s) to be flagged for deletion. (Setting `GDPR_Account__c` to true.)"
                )

                if df["GDPR_Account__c"].sum() > 0:

                    # Drop columns
                    df_accounts = df[["AccountId", "GDPR_Account__c"]]
                    # Rename
                    df_accounts = df_accounts.rename(
                        columns={"AccountId": "Id"}, inplace=False
                    )
                    # Filter
                    df_accounts = df_accounts.loc[df_accounts["GDPR_Account__c"] == 1]
                    # Export
                    print("Exporting to CSV.")
                    df_accounts.to_csv(
                        r"exports/flag_accounts_"
                        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                        + ".csv",
                        encoding="utf-8",
                        index=False,
                    )
                    # Convert to lists of dicts
                    target_data_accounts = df_accounts.to_dict("records")

                    # Push account updates to SFDC
                    try:
                        # Start spinner
                        stop_spinner = threading.Event()
                        spinner_thread = threading.Thread(
                            target=spin, args=(stop_spinner,)
                        )

                        print(
                            "Pushing the GDPR flag update to household accounts in SFDC...",
                            end="",
                            flush=True,
                        )
                        spinner_thread.start()

                        result = sf.bulk.Account.update(
                            target_data_accounts, batch_size=500, use_serial=True
                        )

                        # Stop spinner
                        stop_spinner.set()
                        spinner_thread.join()
                        print("\nDone!")

                        # Print success count
                        success_list = [
                            1 if d["success"] is True else 0 for d in result
                        ]
                        success_emoji = (
                            "✔️"
                            if (len(success_list) - sum(success_list)) == 0
                            else "💥"
                        )
                        print(
                            "OK: "
                            + str(sum(success_list))
                            + ", Fail: "
                            + str(len(success_list) - sum(success_list))
                            + ". "
                            + success_emoji
                        )
                        # Write result to file
                        print("Exporting the results.")
                        with open(
                            r"results/results_flag_accounts_from_bulk_list_"
                            + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
                            + ".txt",
                            "w",
                        ) as f:
                            for item in result:
                                f.write("%s\n" % item)
                    except:
                        # Stop spinner
                        stop_spinner.set()
                        spinner_thread.join()
                        print("\nAccount update error.")

    input("Task completed. 🚀 Press Enter to return to the main menu...")


def delete_flagged_records(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    print("Deleting all flagged records...")

    # Pause
    input("Next step: Connect to SFDC. Press Enter to continue...")

    # Initiate SFDC connection
    sf = Salesforce(
        username=SFDC_USERNAME, password=SFDC_PASSWORD, security_token=SFDC_TOKEN
    )

    # Query cases
    query = """
    SELECT
        Id
    FROM CASE WHERE Contact.GDPR__c = true
    """

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print(
        "Querying all cases related to contacts flagged for deletion in SFDC...",
        end="",
        flush=True,
    )
    spinner_thread.start()

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Run query
    data = sf.query_all(query)

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # To dataframe
    df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
    print(f"{df.shape[0]} case(s) found.")

    # Export
    print("Exporting to CSV.")
    os.makedirs("exports", exist_ok=True)
    df.to_csv(
        r"exports/gdpr_contact_cases_to_delete_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".csv",
        encoding="utf-8",
        index=False,
    )

    # Convert to lists of dicts
    target_data_cases = df.to_dict("records")

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print("Deleting the cases in SFDC...", end="", flush=True)
    spinner_thread.start()

    # Push to SFDC
    result = sf.bulk.Case.delete(target_data_cases, batch_size=500, use_serial=True)

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # Print success count
    success_list = [1 if d["success"] is True else 0 for d in result]
    success_emoji = "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
    print(
        "OK: "
        + str(sum(success_list))
        + ", Fail: "
        + str(len(success_list) - sum(success_list))
        + ". "
        + success_emoji
    )

    # Write result to file
    print("Exporting the results.")
    os.makedirs("results", exist_ok=True)
    with open(
        r"results/results_gdpr_contact_cases_to_delete_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".txt",
        "w",
    ) as f:
        for item in result:
            f.write("%s\n" % item)

    # Query contacts
    query = """
    SELECT
        Id
    FROM Contact WHERE GDPR__c = true
    """

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print("Querying all contacts flagged for deletion in SFDC...", end="", flush=True)
    spinner_thread.start()

    # Remove first and last line
    query = "\n".join(query.split("\n")[1:-1])
    # Run query
    data = sf.query_all(query)

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # To dataframe
    df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
    print(f"{df.shape[0]} contact(s) found.")

    # Export
    print("Exporting to CSV.")
    os.makedirs("exports", exist_ok=True)
    df.to_csv(
        r"exports/gdpr_contacts_to_delete_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".csv",
        encoding="utf-8",
        index=False,
    )

    # Convert to lists of dicts
    target_data_contacts = df.to_dict("records")

    # Start spinner
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))

    print("Deleting the contacts in SFDC...", end="", flush=True)
    spinner_thread.start()

    # Push to SFDC
    result = sf.bulk.Contact.delete(
        target_data_contacts, batch_size=500, use_serial=True
    )

    # Stop spinner
    stop_spinner.set()
    spinner_thread.join()
    print("\nDone!")

    # Print success count
    success_list = [1 if d["success"] is True else 0 for d in result]
    success_emoji = "✔️" if (len(success_list) - sum(success_list)) == 0 else "💥"
    print(
        "OK: "
        + str(sum(success_list))
        + ", Fail: "
        + str(len(success_list) - sum(success_list))
        + ". "
        + success_emoji
    )

    # Write result to file
    print("Exporting the results.")
    os.makedirs("results", exist_ok=True)
    with open(
        r"results/results_gdpr_contacts_to_delete_"
        + datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
        + ".txt",
        "w",
    ) as f:
        for item in result:
            f.write("%s\n" % item)

    input("Task completed. 🚀 Press Enter to return to the main menu...")


def spin(stop):
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    while not stop.is_set():
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write("\b")
        time.sleep(0.1)


if __name__ == "__main__":
    main()

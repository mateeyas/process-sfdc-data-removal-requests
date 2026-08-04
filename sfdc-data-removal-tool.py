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

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich import print as rprint

console = Console()


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


def print_result_summary(result, label="records"):
    """Print a summary of a Salesforce bulk operation result."""
    success_count = sum(1 for d in result if d["success"] is True)
    fail_count = len(result) - success_count
    if fail_count == 0:
        console.print(f"  [green]✔  OK: {success_count}  |  Fail: {fail_count}[/green]")
    else:
        console.print(f"  [red]✘  OK: {success_count}  |  Fail: {fail_count}[/red]")
    return success_count, fail_count


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


def get_file_format():
    """Ask the user whether the file is XLSX or CSV using an InquirerPy prompt."""
    print()
    questions = [
        {
            "type": "list",
            "name": "format",
            "message": "What format is the file?",
            "choices": [
                {"name": "Excel (.xlsx)", "value": "x"},
                {"name": "CSV (.csv)", "value": "c"},
            ],
        }
    ]
    answers = prompt(questions)
    return answers["format"]


def main():
    try:
        # Ensure proper encoding
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)

        console.print(Panel.fit(
            "[bold cyan]🚀  Contact Removal Tool[/bold cyan]\n"
            "[dim]SFDC data removal · unsubscribe · credit card removal[/dim]",
            border_style="cyan",
        ))

        console.print("Getting things ready…")

        # Set working directory
        def get_script_dir():
            if getattr(sys, "frozen", False):
                return os.path.dirname(sys.executable)
            else:
                return os.path.dirname(os.path.abspath(__file__))

        script_dir = get_script_dir()
        os.chdir(script_dir)

        # Get SFDC credentials
        config = ConfigParser()
        config_file_path = "sfdc.ini"

        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"{config_file_path} does not exist.")

        config.read(config_file_path)

        SFDC_USERNAME = config.get("secrets", "SFDC_USERNAME")
        SFDC_PASSWORD = config.get("secrets", "SFDC_PASSWORD")
        SFDC_TOKEN = config.get("secrets", "SFDC_TOKEN")

        if not SFDC_USERNAME or not SFDC_PASSWORD or not SFDC_TOKEN:
            raise ValueError("One or more SFDC credentials are not set in config file.")

        console.print("[green]✔  Credentials loaded.[/green]")

        while True:
            user_action = get_user_action()

            if user_action == "Process a list of removal requests":
                handle_requests(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Process a list of email addresses":
                handle_email_list(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Delete all flagged records in SFDC":
                delete_flagged_records(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)
            elif user_action == "Exit":
                console.print("Goodbye. 👋")
                break

    except Exception as e:
        console.print_exception()
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
    Falls back to a manual path prompt if no file is selected from the dialog.
    Returns the selected file path or empty string if the user cancels.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()
    file_path = filedialog.askopenfilename(parent=root)
    root.destroy()

    if not file_path:
        console.print("[dim]No file chosen from dialog. Enter the path manually (or leave blank to cancel):[/dim]")
        manual = input("  File path: ").strip()
        file_path = manual

    return file_path


def connect_to_sfdc(username, password, token):
    """Connect to Salesforce and return the client, with a spinner."""
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))
    console.print("Connecting to Salesforce…", end="")
    spinner_thread.start()
    try:
        sf = Salesforce(username=username, password=password, security_token=token)
    finally:
        stop_spinner.set()
        spinner_thread.join()
    console.print("\r[green]✔  Connected to Salesforce.[/green]          ")
    return sf


def run_query_with_spinner(sf, query, label="Querying SFDC"):
    """Run a SOQL query with a spinner, return the result data."""
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))
    console.print(f"{label}…", end="")
    spinner_thread.start()
    try:
        data = sf.query_all(query)
    finally:
        stop_spinner.set()
        spinner_thread.join()
    console.print(f"\r[green]✔  {label} — done.[/green]          ")
    return data


def push_update_with_spinner(sf_bulk_op, records, batch_size, label="Pushing updates to SFDC"):
    """Run a Salesforce bulk update/delete with a spinner, return the result."""
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spin, args=(stop_spinner,))
    console.print(f"{label}…", end="")
    spinner_thread.start()
    try:
        result = sf_bulk_op(records, batch_size=batch_size, use_serial=True)
    finally:
        stop_spinner.set()
        spinner_thread.join()
    console.print(f"\r[green]✔  {label} — done.[/green]          ")
    return result


def write_results_file(result, path):
    """Write raw bulk operation results to a text file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for item in result:
            f.write("%s\n" % item)
    console.print(f"  [dim]Results saved → {path}[/dim]")


def handle_requests(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    console.rule("[bold]Process Removal Requests[/bold]")

    # Choose source format
    source_key = get_source_format()
    source_config = SOURCE_FORMATS[source_key]
    console.print(f"Source format: [cyan]{source_config['label']}[/cyan]")

    # Choose file format
    file_format = get_file_format()

    # Pick file
    file_path = open_file_dialog_focused()
    if not file_path:
        console.print("[yellow]No file selected. Returning to the main menu.[/yellow]")
        return

    try:
        if file_format == "x":
            df_temp = pd.read_excel(file_path, nrows=0)
        else:
            df_temp = pd.read_csv(file_path, nrows=0)

        dtype_dict = {}
        for desired_col, dtype in source_config["dtypes"].items():
            actual_col = find_column_case_insensitive(df_temp, desired_col)
            if actual_col:
                dtype_dict[actual_col] = dtype

        if file_format == "x":
            df_requests = pd.read_excel(file_path, dtype=dtype_dict)
        else:
            df_requests = pd.read_csv(file_path, dtype=dtype_dict)

    except Exception as e:
        console.print(f"[red]Error loading file: {e}[/red]")
        console.print_exception()
        return

    console.print(f"[green]✔  {df_requests.shape[0]} requests loaded.[/green]")

    # Validate required columns
    task_assignee_col = find_column_case_insensitive(df_requests, source_config["assignee_col"])
    request_type_col = find_column_case_insensitive(df_requests, source_config["request_type_col"])
    email_col = find_column_case_insensitive(df_requests, source_config["email_col"])

    missing = []
    if not task_assignee_col:
        missing.append(source_config["assignee_col"])
    if not request_type_col:
        missing.append(source_config["request_type_col"])
    if not email_col:
        missing.append(source_config["email_col"])

    if missing:
        console.print(f"[red]Error: could not find required column(s): {missing}[/red]")
        console.print(f"Available columns: {list(df_requests.columns)}")
        return

    # Filter for Salesforce tasks
    df_requests = df_requests.loc[
        df_requests[task_assignee_col] == "Salesforce"
    ].reset_index(drop=True)
    console.print(f"  {df_requests.shape[0]} requests assigned to Salesforce.")

    # Categorise
    conditions = [
        df_requests[request_type_col].isin(source_config["data_removal_values"]),
        df_requests[request_type_col].isin(source_config["unsubscribe_values"]),
        df_requests[request_type_col].isin(source_config["credit_card_values"]),
    ]
    choices = ["data_removal", "unsubscribe", "credit_card_removal"]
    df_requests["request_type"] = np.select(conditions, choices, default="unknown")

    unmatched_requests = df_requests[df_requests["request_type"] == "unknown"]
    if not unmatched_requests.empty:
        console.print(
            f"[yellow]⚠  {len(unmatched_requests)} request(s) had an unrecognised type and will be skipped.[/yellow]"
        )
        console.print(f"  Unrecognised values: {unmatched_requests[request_type_col].unique().tolist()}")

    # Extract email lists
    data_removal_email_list = df_requests.loc[df_requests["request_type"] == "data_removal"][email_col].tolist()
    unsubscribe_email_list = df_requests.loc[df_requests["request_type"] == "unsubscribe"][email_col].tolist()
    cc_removal_email_list = df_requests.loc[df_requests["request_type"] == "credit_card_removal"][email_col].tolist()

    console.print(f"  Data removal:      [bold]{len(data_removal_email_list)}[/bold]")
    console.print(f"  Unsubscribe:       [bold]{len(unsubscribe_email_list)}[/bold]")
    console.print(f"  Credit card:       [bold]{len(cc_removal_email_list)}[/bold]")

    # Escape apostrophes
    data_removal_email_list = [e.replace("'", "\\'") for e in data_removal_email_list]
    unsubscribe_email_list = [e.replace("'", "\\'") for e in unsubscribe_email_list]
    cc_removal_email_list = [e.replace("'", "\\'") for e in cc_removal_email_list]

    data_removal_email_list_str = ",".join(f"'{x}'" for x in data_removal_email_list)
    unsubscribe_email_list_str = ",".join(f"'{x}'" for x in unsubscribe_email_list)
    cc_removal_email_list_str = ",".join(f"'{x}'" for x in cc_removal_email_list)

    sf = connect_to_sfdc(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)

    # ── Data removal contacts & accounts ─────────────────────────────────────
    console.rule("[dim]Data removal[/dim]")

    query = (
        "SELECT Id, AccountId, Account.RecordTypeId "
        f"FROM Contact WHERE Email IN ({data_removal_email_list_str})"
    )
    data = run_query_with_spinner(sf, query, "Querying contacts and accounts")

    rows = []
    for item in data["records"]:
        row = {}
        try:
            row["Id"] = item["Id"]
            row["AccountId"] = item["AccountId"]
        except Exception as exc:
            console.print(f"[yellow]  Warning: could not read Id/AccountId from record: {exc}[/yellow]")
        try:
            row["RecordTypeId"] = item["Account"]["RecordTypeId"]
        except Exception as exc:
            console.print(f"[yellow]  Warning: could not read RecordTypeId from record: {exc}[/yellow]")
        rows.append(row)

    df = pd.DataFrame(rows)
    console.print(f"  {df.shape[0]} contact(s) found.")

    df["GDPR__c"] = 1
    df["GDPR_Account__c"] = np.where(df["RecordTypeId"] == "012d0000000W68QAAS", 1, 0)

    console.print(f"  Flagging [bold]{df.shape[0]}[/bold] contact(s) for deletion (GDPR__c = true).")
    console.print(f"  Flagging [bold]{int(df['GDPR_Account__c'].sum())}[/bold] household account(s) for deletion (GDPR_Account__c = true).")

    df_contacts = df[["Id", "GDPR__c"]]
    df_accounts = df[["AccountId", "GDPR_Account__c"]].rename(columns={"AccountId": "Id"})
    df_accounts = df_accounts.loc[df_accounts["GDPR_Account__c"] == 1]

    os.makedirs("exports", exist_ok=True)
    ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
    contacts_export = f"exports/data_removal_contacts_{ts}.csv"
    accounts_export = f"exports/data_removal_accounts_{ts}.csv"
    df_contacts.to_csv(contacts_export, encoding="utf-8", index=False)
    df_accounts.to_csv(accounts_export, encoding="utf-8", index=False)
    console.print(f"  [dim]Exported → {contacts_export}[/dim]")
    console.print(f"  [dim]Exported → {accounts_export}[/dim]")

    result = push_update_with_spinner(
        sf.bulk.Contact.update,
        df_contacts.to_dict("records"),
        batch_size=20,
        label="Flagging contacts",
    )
    ok, fail = print_result_summary(result, "contacts")
    write_results_file(result, f"results/results_data_removal_contacts_{ts}.txt")

    result = push_update_with_spinner(
        sf.bulk.Account.update,
        df_accounts.to_dict("records"),
        batch_size=20,
        label="Flagging household accounts",
    )
    ok, fail = print_result_summary(result, "accounts")
    write_results_file(result, f"results/results_data_removal_accounts_{ts}.txt")

    # ── Unsubscribe contacts ──────────────────────────────────────────────────
    console.rule("[dim]Unsubscribe[/dim]")

    if len(unsubscribe_email_list) > 0:
        query = (
            "SELECT Id "
            f"FROM Contact WHERE Email IN ({unsubscribe_email_list_str})"
        )
        data = run_query_with_spinner(sf, query, "Querying unsubscribe contacts")

        df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
        console.print(f"  {df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:
            df["HasOptedOutOfEmail"] = 1
            df["Marketing_Status__c"] = "No Marketing"

            ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
            unsub_export = f"exports/unsubscribe_contacts_{ts}.csv"
            df.to_csv(unsub_export, encoding="utf-8", index=False)
            console.print(f"  [dim]Exported → {unsub_export}[/dim]")

            result = push_update_with_spinner(
                sf.bulk.Contact.update,
                df.to_dict("records"),
                batch_size=500,
                label="Updating unsubscribe contacts",
            )
            ok, fail = print_result_summary(result, "contacts")
            write_results_file(result, f"results/results_unsubscribe_contacts_{ts}.txt")
    else:
        console.print("  No unsubscribe requests to process.")

    # ── Credit card removal ───────────────────────────────────────────────────
    console.rule("[dim]Credit card removal[/dim]")

    if len(cc_removal_email_list) > 0:
        df_cc = df_requests[df_requests.request_type == "credit_card_removal"].reset_index(drop=True)

        query = (
            "SELECT Id, Email, AccountId, Account.RecordTypeId "
            f"FROM Contact WHERE Email IN ({cc_removal_email_list_str})"
        )
        data = run_query_with_spinner(sf, query, "Querying credit card removal contacts")

        rows = []
        for item in data["records"]:
            row = {}
            try:
                row["Id"] = item["Id"]
                row["AccountId"] = item["AccountId"]
                row["Email"] = item["Email"]
            except Exception as exc:
                console.print(f"[yellow]  Warning: could not read record fields: {exc}[/yellow]")
            try:
                row["RecordTypeId"] = item["Account"]["RecordTypeId"]
            except Exception as exc:
                console.print(f"[yellow]  Warning: could not read RecordTypeId: {exc}[/yellow]")
            rows.append(row)

        df = pd.DataFrame(rows)
        console.print(f"  {df.shape[0]} contact(s) found.")

        if df.shape[0] > 0:
            df["sfdc_contact_link"] = "https://rs.lightning.force.com/lightning/r/" + df["Id"] + "/view"
            df["Email"] = df["Email"].str.lower()
            df_cc[email_col] = df_cc[email_col].str.lower()

            df_cc_final = df_cc.merge(df, left_on=email_col, right_on="Email", how="left")

            ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
            cc_export = f"exports/cc_removal_requests_with_contacts_{ts}.csv"
            df_cc_final.to_csv(cc_export, encoding="utf-8", index=False)
            console.print(f"  [dim]Exported → {cc_export}[/dim]")
            console.print(
                "[yellow]  ⚠  Don't forget to open the exported file and manually check SFDC for credit card numbers.[/yellow]"
            )
    else:
        console.print("  No credit card removal requests to process.")

    console.print()
    input("Task completed. 🚀  Press Enter to return to the main menu…")


def handle_email_list(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    console.rule("[bold]Process Email List[/bold]")

    file_path = open_file_dialog_focused()
    if not file_path:
        console.print("[yellow]No file selected. Returning to the main menu.[/yellow]")
        return

    try:
        with open(file_path) as f:
            contacts = [line.rstrip() for line in f.readlines()]
    except Exception as e:
        console.print(f"[red]Error loading file: {e}[/red]")
        console.print_exception()
        return

    n = 300
    contacts_chunks = [contacts[i: i + n] for i in range(0, len(contacts), n)]
    total_chunks = len(contacts_chunks)

    console.print(f"[green]✔  {len(contacts)} email address(es) loaded.[/green]")
    console.print(f"  Splitting into {total_chunks} chunk(s) of up to {n}.")

    sf = connect_to_sfdc(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)

    os.makedirs("exports", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    for chunk_index, chunk in enumerate(contacts_chunks, start=1):
        console.rule(f"[dim]Chunk {chunk_index} / {total_chunks}[/dim]")

        chunk = [email.replace("'", "\\'") for email in chunk]
        contacts_str = ",".join(f"'{x}'" for x in chunk)

        query = (
            "SELECT Id, AccountId, Account.RecordTypeId "
            f"FROM Contact WHERE Email IN ({contacts_str})"
        )
        data = run_query_with_spinner(sf, query, "Querying contacts")

        if not data["records"]:
            console.print("  No contacts found for this chunk.")
            continue

        rows = []
        for item in data["records"]:
            row = {}
            try:
                row["Id"] = item["Id"]
                row["AccountId"] = item["AccountId"]
            except Exception as exc:
                console.print(f"[yellow]  Warning: could not read Id/AccountId: {exc}[/yellow]")
            try:
                row["RecordTypeId"] = item["Account"]["RecordTypeId"]
            except Exception as exc:
                console.print(f"[yellow]  Warning: could not read RecordTypeId: {exc}[/yellow]")
            rows.append(row)

        df = pd.DataFrame(rows)
        console.print(f"  {df.shape[0]} contact(s) to flag for deletion (GDPR__c = true).")

        if df.shape[0] > 0:
            df["GDPR__c"] = 1
            df_contacts = df[["Id", "GDPR__c"]]

            ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
            contacts_export = f"exports/flag_contacts_from_bulk_list_{ts}.csv"
            df_contacts.to_csv(contacts_export, encoding="utf-8", index=False)
            console.print(f"  [dim]Exported → {contacts_export}[/dim]")

            try:
                result = push_update_with_spinner(
                    sf.bulk.Contact.update,
                    df_contacts.to_dict("records"),
                    batch_size=500,
                    label="Flagging contacts",
                )
                ok, fail = print_result_summary(result, "contacts")
                write_results_file(result, f"results/results_flag_contacts_from_bulk_list_{ts}.txt")
            except Exception as exc:
                console.print(f"[red]  Contact update error: {exc}[/red]")
                console.print_exception()

            df["GDPR_Account__c"] = np.where(df["RecordTypeId"] == "012d0000000W68QAAS", 1, 0)
            account_flag_count = int(df["GDPR_Account__c"].sum())
            console.print(f"  {account_flag_count} household account(s) to flag (GDPR_Account__c = true).")

            if account_flag_count > 0:
                df_accounts = (
                    df[["AccountId", "GDPR_Account__c"]]
                    .rename(columns={"AccountId": "Id"})
                    .loc[lambda d: d["GDPR_Account__c"] == 1]
                )
                accounts_export = f"exports/flag_accounts_{ts}.csv"
                df_accounts.to_csv(accounts_export, encoding="utf-8", index=False)
                console.print(f"  [dim]Exported → {accounts_export}[/dim]")

                try:
                    result = push_update_with_spinner(
                        sf.bulk.Account.update,
                        df_accounts.to_dict("records"),
                        batch_size=500,
                        label="Flagging household accounts",
                    )
                    ok, fail = print_result_summary(result, "accounts")
                    write_results_file(result, f"results/results_flag_accounts_from_bulk_list_{ts}.txt")
                except Exception as exc:
                    console.print(f"[red]  Account update error: {exc}[/red]")
                    console.print_exception()

    console.print()
    input("Task completed. 🚀  Press Enter to return to the main menu…")


def delete_flagged_records(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN):
    console.rule("[bold red]Delete Flagged Records[/bold red]")

    console.print(Panel(
        "[bold red]WARNING[/bold red]\n"
        "This will permanently delete all contacts and cases flagged with GDPR__c = true from Salesforce.\n"
        "This action [bold]cannot be undone[/bold].",
        border_style="red",
    ))

    questions = [
        {
            "type": "confirm",
            "name": "confirmed",
            "message": "Are you sure you want to proceed?",
            "default": False,
        }
    ]
    if not prompt(questions)["confirmed"]:
        console.print("[yellow]Cancelled. Returning to the main menu.[/yellow]")
        return

    sf = connect_to_sfdc(SFDC_USERNAME, SFDC_PASSWORD, SFDC_TOKEN)

    os.makedirs("exports", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    # ── Delete cases ──────────────────────────────────────────────────────────
    console.rule("[dim]Cases[/dim]")

    query = "SELECT Id FROM CASE WHERE Contact.GDPR__c = true"
    data = run_query_with_spinner(sf, query, "Querying flagged cases")

    df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
    console.print(f"  {df.shape[0]} case(s) found.")

    ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
    cases_export = f"exports/gdpr_contact_cases_to_delete_{ts}.csv"
    df.to_csv(cases_export, encoding="utf-8", index=False)
    console.print(f"  [dim]Exported → {cases_export}[/dim]")

    result = push_update_with_spinner(
        sf.bulk.Case.delete,
        df.to_dict("records"),
        batch_size=500,
        label="Deleting cases",
    )
    ok, fail = print_result_summary(result, "cases")
    write_results_file(result, f"results/results_gdpr_contact_cases_to_delete_{ts}.txt")

    # ── Delete contacts ───────────────────────────────────────────────────────
    console.rule("[dim]Contacts[/dim]")

    query = "SELECT Id FROM Contact WHERE GDPR__c = true"
    data = run_query_with_spinner(sf, query, "Querying flagged contacts")

    df = pd.DataFrame(data["records"]).drop(["attributes"], axis=1, errors="ignore")
    console.print(f"  {df.shape[0]} contact(s) found.")

    ts = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M-%S")
    contacts_export = f"exports/gdpr_contacts_to_delete_{ts}.csv"
    df.to_csv(contacts_export, encoding="utf-8", index=False)
    console.print(f"  [dim]Exported → {contacts_export}[/dim]")

    result = push_update_with_spinner(
        sf.bulk.Contact.delete,
        df.to_dict("records"),
        batch_size=500,
        label="Deleting contacts",
    )
    ok, fail = print_result_summary(result, "contacts")
    write_results_file(result, f"results/results_gdpr_contacts_to_delete_{ts}.txt")

    console.print()
    input("Task completed. 🚀  Press Enter to return to the main menu…")


def spin(stop):
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    while not stop.is_set():
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write("\b")
        time.sleep(0.1)


if __name__ == "__main__":
    main()

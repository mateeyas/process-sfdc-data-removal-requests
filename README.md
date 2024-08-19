# SFDC Data Removal Tool

This tool was created for IXL and Rosetta Stone Salesforce.com admins to help them process data removal requests received via the OneTrust platform.

## Description

Data removal and unsubscribe requests exported from OneTrust can be handled in bulk by this tool. Bulk email lists can also be processed.

## Getting Started

### Dependencies

To run the script using Python or to build the executable, you will need to install the following dependencies:

- `simple-salesforce`
- `pandas`
- `numpy`
- `InquirerPy`

### Running the Script (Using Python)

To run the script using Python directly, follow these steps:

1. **Install Dependencies**: Ensure all dependencies are installed:

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Script**: After installing the dependencies, you can run the Python script by executing the following command in the terminal:

   ```bash
   python process-sfdc-data-removal-requests.py
   ```

3. **Configure SFDC Credentials**: Make sure the `sfdc.ini` file is in the same folder as the script, containing the following format:

   ```
   [secrets]
   SFDC_USERNAME=user@abc.com
   SFDC_PASSWORD=abcdefgh12345678
   SFDC_TOKEN=12345678abcdefgh
   ```

4. **Follow Instructions**: After running the script, follow the instructions on the screen. You will be prompted to provide either an XLSX or CSV file for OneTrust requests or a TXT file with email addresses.

### Building and Running the Executable (Using PyInstaller)

If you prefer to distribute or run the tool as an executable file, you can build it with `PyInstaller`.

#### Steps to Build the Executable:

1. **Install PyInstaller**:

   ```bash
   pip install pyinstaller
   ```

2. **Build the Executable**: Run the following command to package the script into an executable:

   ```bash
   pyinstaller --onefile --name "data-removal-tool-0.2" --icon=rocket.ico process-sfdc-data-removal-requests.py
   ```

   This will create a single executable file (`data-removal-tool-0.2.exe`) in the `dist` directory.

3. **Prepare SFDC Credentials**: Ensure that the `sfdc.ini` file containing the Salesforce credentials is placed in the same directory as the executable:

   ```
   [secrets]
   SFDC_USERNAME=user@abc.com
   SFDC_PASSWORD=abcdefgh12345678
   SFDC_TOKEN=12345678abcdefgh
   ```

4. **Run the Executable**: Double-click the executable file or run it from the command line:

   ```bash
   ./dist/data-removal-tool-0.2.exe
   ```

   Follow the instructions displayed on the screen to process OneTrust requests or bulk email lists.

### Installation (Executable)

When using the executable file, no installation is necessary. You only need the `sfdc.ini` file with Salesforce.com credentials in the same folder as the executable.

### Run (Executable)

Just run the executable file and follow the instructions on the screen. You should already have a list of OneTrust requests in an XLSX or CSV file.

If you need to process a bulk email list, it should be a TXT file with each email address on a new line.

## Help

Feel free to reach out to me if you have any questions or suggestions.

## Author

Matthias Ragus ([matt@tala.dev](mailto:matt@tala.dev))

## Version History

* 0.2
    * Added a simple user interface.
    * Improved the error handling.
    * Fixed the missing SFDC client initialization in the deletion task when the other tasks are skipped.
    * May contain bugs.

* 0.1
    * Initial release.
    * May contain bugs.

## License

This project is licensed under the MIT License.

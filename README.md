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
   python sfdc-data-removal-tool.py
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
   pyinstaller --onefile --name "data-removal-tool-0.x" --icon=rocket.ico --version-file=version_info.txt --noupx --console --clean --noconfirm sfdc-data-removal-tool.py
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

## Windows Security Notice

When running the executable for the first time, Windows may display a security warning because the application is not digitally signed. This is normal behavior for unsigned executables.

**If Windows blocks the executable:**

1. **Windows Defender SmartScreen Warning:**

   - Click "More info"
   - Click "Run anyway"

2. **If the file is quarantined:**

   - Open Windows Security (Windows Defender)
   - Go to "Virus & threat protection"
   - Click "Protection history"
   - Find the quarantined file and restore it
   - Add the executable to exclusions if needed

3. **Alternative method:**
   - Right-click the executable
   - Select "Properties"
   - Check "Unblock" if present
   - Click "OK"

**Why this happens:**

- The executable is not digitally signed with a code signing certificate
- Windows treats unsigned executables as potentially unsafe
- This is a security feature, not a virus detection

The application is safe to run and contains no malicious code.

## Version History

- 0.7

  - Improved UI with `rich` for coloured output, section headers, and summary banners.
  - Replaced bare `input()` file-format prompt with an InquirerPy list selector.
  - Added explicit confirmation step before deleting flagged records.
  - Surfaces unmatched/unrecognised request types as a warning instead of silently skipping them.
  - File dialog now falls back to a manual path prompt if dismissed without a selection.
  - Extracted shared helpers to eliminate repeated spinner/query/update/result patterns.
  - Fixed bare `except: pass` blocks to log exceptions properly.
  - Removed leftover debug `df.shape` calls.

- 0.4

  - Disabled UPX compression to reduce antivirus false positives
  - Added version information to executable
  - Improved Windows compatibility

- 0.3

  - Fixed the missing SFDC config parameter passing.
  - Added ASCII art.
  - Fixed emoji encoding issues.

- 0.2

  - Added a simple user interface.
  - Improved the error handling.
  - Fixed the missing SFDC client initialization in the deletion task when the other tasks are skipped.
  - May contain bugs.

- 0.1

  - Initial release.
  - May contain bugs.

## License

This project is licensed under the MIT License.

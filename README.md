# Process SFDC data removal requests

This tool was created for the IXL and Rosetta Stone Salesforce.com admins to help process data removal requests received via the OneTrust platform.

## Description

Data removal and unsubscribe requests exported from OneTrust can be handled in bulk by this tool. Bulk email lists can also processed.

## Getting Started

### Dependencies

There are no particular dependencies.

### Installation

When using the executable file, no installation is necessary. However, an `sfdc.ini` file must be in the same folder containing Salesforce.com credentials. The `sfdc.ini` file should have this format:

```
[secrets]
SFDC_USERNAME=user@abc.com
SFDC_PASSWORD=abcdefgh12345678
SFDC_TOKEN=12345678abcdefgh
```

### Run

Just run the executable file and follow the instructions on the screen. You should already have a list of OneTrust requests in an XLSX or CSV file.

If you need to process a bulk email list, it should be a TXT file with each email address on a new line.

## Help

Feel free to reach out to me if you have any questions or suggestions.

## Author

Matthias Ragus

## Version History

* 0.1
    * Initial Release
    * May contain bugs

## License

This project is licensed under the MIT License.

# speedhive-tools

## Overview
`speedhive-tools` is a Python-based toolkit designed to interact with the MYLAPS Speedhive Event Results API.  
Its primary intent is to **automate the extraction and formatting of track record announcements** (e.g., "New Track Record") for racing organizations.  

While the initial implementation focuses on generating a clean JSON file of track records, the architecture is **fully extendable**. You can easily add methods to:
- Pull classifications, lap charts, or timing data
- Filter by date ranges or event types
- Export to CSV or databases for analytics

---

## Features
- **Search organizations** by ID or name
- **Traverse events and sessions** recursively (handles nested groups)
- **Extract announcements** containing "New Track Record"
- **Parse structured data**: class abbreviation, lap time, driver name, marque, and date
- **Output JSON** in a normalized format for easy consumption

---

## Example Workflow
1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/speedhive-tools.git
   cd speedhive-tools
   ```
2. Install dependencies:
   ```bash
   pip install requests
   ```
3. Run the example script:
   ```bash
   python speedhive_example_runner.py
   ```
   This will:
   - Export records for organization ID `30476` (Waterford Hills)
   - Export records for organization name `"Waterford Hills"`
   - Save outputs as `waterford_hills_by_id.json` and `waterford_hills_by_name.json`

---

## Output Format
```json
{
  "records": [
    {
      "classAbbreviation": "FA",
      "lapTime": "1:01.861",
      "driverName": "J. Lewis Cooper, Jr",
      "marque": "Swift 01 4A",
      "date": "2009-05-10"
    }
  ]
}
```

---

## Extending the Client
The `SpeedHiveClient` class is modular:
- Add new methods for `/classification` or `/lapchart` endpoints
- Implement filters for date ranges or event types
- Support CSV or database export

---

## License
MIT License – see LICENSE.

---

## Contributing
Pull requests are welcome! Please open an issue first to discuss major changes.

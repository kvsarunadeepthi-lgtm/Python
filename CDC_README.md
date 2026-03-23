# CDC Framework - Change Data Capture for Python

A robust Python framework for Change Data Capture (CDC) that tracks inserts, updates, and deletes in CSV files and applies them to an Oracle database using the SCD Type 2 (Slowly Changing Dimensions) pattern.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Framework Architecture](#framework-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [Change Tracking Details](#change-tracking-details)
- [Examples](#examples)

---

## Overview

This CDC framework enables you to:
1. **Read CSV files** as data sources
2. **Compare with previous snapshots** to detect changes
3. **Track three types of changes**: INSERT, UPDATE, DELETE
4. **Write to Oracle database** with complete audit trail
5. **Maintain SCD Type 2** slowly changing dimensions pattern
6. **Identify exact column modifications** with timestamps

## Features

✅ **Change Detection**: Automatically detects INSERT, UPDATE, DELETE changes  
✅ **SCD Type 2 Implementation**: Expires old records, inserts new versions  
✅ **Timestamp Tracking**: Records when changes occurred  
✅ **Column-level Tracking**: Identifies exactly which columns changed  
✅ **Oracle Integration**: Direct database writes with transactions  
✅ **Snapshot Management**: Maintains state for incremental processing  
✅ **JSON Configuration**: Easy setup via configuration files  
✅ **Comprehensive Logging**: Detailed tracking of all operations  

---

## Framework Architecture

### Core Modules

```
┌─────────────────────────────────────────────┐
│         CDC_MAIN_EXAMPLE.PY                  │
│      (Entry Point / Orchestration)           │
└────────────────────┬────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│  CDC_CONFIG │ │  CDC_ENGINE  │ │ CHANGE_      │
│             │ │              │ │ TRACKER      │
│ - Load JSON │ │ - Orchestrate│ │ - Detect     │
│ - Validate  │ │ - Load CSV   │ │   changes    │
└─────────────┘ │ - Apply DB   │ └──────────────┘
                 └──────┬───────┘
                        │
                        ▼
              ┌──────────────────┐
              │  DB_CONNECTOR    │
              │                  │
              │ - Connect Oracle │
              │ - Insert/Update  │
              │ - Delete (expire)│
              └──────────────────┘
```

### File Structure

```
python/
├── cdc_config.py              # Configuration handling
├── cdc_engine.py              # Main orchestration
├── change_tracker.py          # Change detection logic
├── db_connector.py            # Oracle database operations
├── cdc_main_example.py        # Usage examples
├── cdc_config_example.json    # Example configuration
├── sample_customers.csv       # Sample data file
└── README.md                  # This file
```

---

## Installation

### Prerequisites
- Python 3.7+
- pandas library
- cx_Oracle library (for Oracle connectivity)

### Setup

1. **Install required packages**:
```bash
pip install pandas cx-Oracle
```

2. **Copy framework files to your project**:
```bash
# All .py files should be in the same directory
cdc_config.py
cdc_engine.py
change_tracker.py
db_connector.py
```

3. **Create your configuration JSON** (see Configuration section below)

4. **Prepare your CSV data file**

---

## Configuration

The framework is configured using a JSON file. Here's the structure:

### Configuration File Format (cdc_config.json)

```json
{
  "table_name": "customer",
  "source_file_path": "data/customers.csv",
  "oracle_table_name": "CUSTOMERS_CDC",
  "business_keys": ["CUSTOMER_ID"],
  "timestamp_column": "CDC_TIMESTAMP",
  "start_date_column": "START_DATE",
  "end_date_column": "END_DATE",
  "row_status_column": "RECORD_STATUS",
  "columns": [
    {
      "name": "CUSTOMER_ID",
      "data_type": "NUMBER(10)",
      "is_primary_key": true,
      "is_business_key": true,
      "nullable": false
    },
    {
      "name": "CUSTOMER_NAME",
      "data_type": "VARCHAR2(100)",
      "is_primary_key": false,
      "is_business_key": false,
      "nullable": false
    }
  ]
}
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `table_name` | Yes | Logical name for the table (used for snapshots) |
| `source_file_path` | Yes | Path to CSV file |
| `oracle_table_name` | Yes | Target Oracle table name |
| `business_keys` | Yes | List of columns that uniquely identify a record |
| `columns` | Yes | Array of column definitions |
| `timestamp_column` | No | Column storing CDC timestamp (default: CDC_TIMESTAMP) |
| `start_date_column` | No | Column for record valid start date (default: START_DATE) |
| `end_date_column` | No | Column for record expiry date (default: END_DATE) |
| `row_status_column` | No | Column for record status (default: RECORD_STATUS) |

### Column Definition Fields

```json
{
  "name": "COLUMN_NAME",          // Column name
  "data_type": "VARCHAR2(100)",   // Oracle data type
  "is_primary_key": false,        // Primary key indicator
  "is_business_key": true,        // Business key indicator
  "nullable": true                // NULL allowed
}
```

**Important**: 
- At least one column must be marked as `is_business_key: true`
- Business keys are used to identify records for change detection
- For SCD Type 2, typically use the natural business key (e.g., CUSTOMER_ID)

---

## Usage

### Basic Usage

```python
from cdc_config import CDCConfigLoader
from cdc_engine import CDCEngine
from db_connector import OracleConnector

# 1. Load configuration
config = CDCConfigLoader.load_config('cdc_config.json')
CDCConfigLoader.validate_config(config)

# 2. Create database connector
db = OracleConnector(
    connection_string='localhost:1521/ORCL',
    username='oracle_user',
    password='password'
)

# 3. Initialize CDC engine
engine = CDCEngine(config, db)

# 4. Run CDC process
success = engine.run()

# 5. Get change summary
if success:
    summary = engine.get_change_summary()
    print(f"Inserts: {summary['inserts']}")
    print(f"Updates: {summary['updates']}")
    print(f"Deletes: {summary['deletes']}")
```

### Run the Example

```bash
# Test mode (no database required)
python cdc_main_example.py

# Production mode (requires Oracle configuration)
# Edit cdc_main_example.py with your connection details and uncomment main()
```

---

## Database Schema

The CDC framework creates tables with the following structure:

### Target Table Format (Oracle)

```sql
CREATE TABLE CUSTOMERS_CDC (
    -- Original columns from CSV
    CUSTOMER_ID VARCHAR2(100),
    CUSTOMER_NAME VARCHAR2(100),
    EMAIL VARCHAR2(100),
    
    -- CDC Tracking Columns
    START_DATE DATE DEFAULT TRUNC(SYSDATE),
    END_DATE DATE DEFAULT TO_DATE('31-DEC-9999', 'DD-MON-YYYY'),
    RECORD_STATUS VARCHAR2(10) DEFAULT 'ACTIVE',
    CDC_TIMESTAMP TIMESTAMP DEFAULT SYSTIMESTAMP,
    CHANGED_COLUMNS VARCHAR2(1000)  -- Comma-separated list of changed columns
);
```

### Record Status Values

| Status | Description |
|--------|-------------|
| ACTIVE | Current version of the record |
| EXPIRED | Previous version (replaced by UPDATE) |
| DELETED | Record was deleted |

### SCD Type 2 Example

**Original Record (Customer ID 1 - John Smith):**
```
START_DATE: 2024-01-01   END_DATE: 9999-12-31   RECORD_STATUS: ACTIVE
ADDRESS: 123 Main St     CITY: New York
```

**When address changes to "456 Oak Ave":**

Old record becomes:
```
START_DATE: 2024-01-01   END_DATE: 2024-01-15   RECORD_STATUS: EXPIRED
ADDRESS: 123 Main St     CITY: New York         CHANGED_COLUMNS: ADDRESS
```

New record (current version):
```
START_DATE: 2024-01-15   END_DATE: 9999-12-31   RECORD_STATUS: ACTIVE
ADDRESS: 456 Oak Ave     CITY: New York
```

---

## Change Tracking Details

### Change Detection Logic

The framework uses **business keys** to identify records and detect changes:

1. **INSERT**: Record exists in current CSV but not in previous snapshot
2. **UPDATE**: Record exists in both, but column values differ
3. **DELETE**: Record exists in previous snapshot but not in current CSV

### Column Change Detection

For UPDATE operations, the framework identifies exactly which columns changed:

```
Name: John Smith → John Smith UPDATED
Email: john@email.com → john.new@email.com
Phone: 555-0001 → 555-0001 (unchanged)

Changed Columns: [NAME, EMAIL]
```

### Timestamp Tracking

- **CDC_TIMESTAMP**: Recorded at the time of CDC processing (not transaction time)
- **START_DATE**: When this version became active
- **END_DATE**: When this version expired (9999-12-31 = still active)

---

## Examples

### Example 1: Simple Customer Data CDC

**CSV File: customers.csv**
```csv
CUSTOMER_ID,CUSTOMER_NAME,EMAIL,STATUS
1,Alice Johnson,alice@email.com,ACTIVE
2,Bob Smith,bob@email.com,ACTIVE
3,Charlie Brown,charlie@email.com,INACTIVE
```

**Configuration: cdc_config.json**
```json
{
  "table_name": "customer",
  "source_file_path": "customers.csv",
  "oracle_table_name": "CUSTOMERS_CDC",
  "business_keys": ["CUSTOMER_ID"],
  "columns": [
    {"name": "CUSTOMER_ID", "data_type": "NUMBER(10)", "is_primary_key": true, "is_business_key": true},
    {"name": "CUSTOMER_NAME", "data_type": "VARCHAR2(100)", "is_business_key": false},
    {"name": "EMAIL", "data_type": "VARCHAR2(100)", "is_business_key": false},
    {"name": "STATUS", "data_type": "VARCHAR2(20)", "is_business_key": false}
  ]
}
```

### Example 2: Composite Business Key

For tables with composite keys (multiple columns uniquely identify a record):

```json
{
  "table_name": "sales",
  "oracle_table_name": "SALES_CDC",
  "business_keys": ["STORE_ID", "PRODUCT_ID", "DATE"],
  "columns": [
    {"name": "STORE_ID", "data_type": "NUMBER(5)", "is_business_key": true},
    {"name": "PRODUCT_ID", "data_type": "NUMBER(10)", "is_business_key": true},
    {"name": "DATE", "data_type": "VARCHAR2(10)", "is_business_key": true},
    {"name": "QUANTITY_SOLD", "data_type": "NUMBER(10)", "is_business_key": false},
    {"name": "AMOUNT", "data_type": "NUMBER(12,2)", "is_business_key": false}
  ]
}
```

### Example 3: Running CDC Incrementally

The framework maintains snapshots, so you can run it multiple times:

**Run 1 - Initial Load:**
- CSV has 100 records
- Previous snapshot is empty
- Result: 100 INSERTs

**Run 2 - After changes:**
- CSV has 101 records (1 new, 5 updated, 0 deleted)
- Previous snapshot had 100 records
- Result: 1 INSERT, 5 UPDATEs

**Run 3 - After more changes:**
- CSV has 99 records (2 deleted, 3 updated)
- Result: 3 UPDATEs, 2 DELETEs

---

## Logging

The framework provides detailed logging at INFO level by default:

```
2024-01-15 10:30:45 - cdc_engine - INFO - Starting CDC process for table: customer
2024-01-15 10:30:45 - cdc_engine - INFO - Loading CSV file: customers.csv
2024-01-15 10:30:45 - cdc_engine - INFO - Loaded 100 rows from CSV
2024-01-15 10:30:46 - cdc_engine - INFO - Detecting changes...
2024-01-15 10:30:46 - change_tracker - INFO - ============================================================
2024-01-15 10:30:46 - change_tracker - INFO - CDC SUMMARY REPORT
2024-01-15 10:30:46 - change_tracker - INFO - Total Changes: 8
2024-01-15 10:30:46 - change_tracker - INFO -   - Inserts: 3
2024-01-15 10:30:46 - change_tracker - INFO -   - Updates: 4
2024-01-15 10:30:46 - change_tracker - INFO -   - Deletes: 1
```

To change log level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)  # For more verbose output
```

---

## Troubleshooting

### "No previous snapshot found"
- This is normal on first run
- Framework will treat all CSV rows as INSERTs
- Subsequent runs will properly detect changes

### Oracle Connection Fails
- Verify `connection_string`, `username`, and `password`
- Ensure Oracle database is running
- Check firewall and network connectivity
- Verify cx_Oracle is installed: `pip list | grep cx-Oracle`

### Missing Columns in CSV
- Ensure CSV has all columns defined in configuration
- Check column names match exactly (case-sensitive)
- Verify CSV is properly formatted

### snapshot file not found
- This is created after the first successful run
- Located in the same directory as the script
- File name: `.cdc_{table_name}_snapshot.json`

---

## Best Practices

1. **Use Composite Keys**: For complex data, use multiple columns as business keys
2. **Regular Snapshots**: Run CDC periodically to capture incremental changes
3. **Monitor Logs**: Check logs for warnings or errors
4. **Test First**: Run in test mode with sample data before production
5. **Backup Database**: Always backup your target database before CDC operations
6. **Version Control**: Keep configuration files in version control
7. **Archive Snapshots**: Periodically archive snapshot files for recovery

---

## Performance Considerations

- CSV files are loaded entirely into memory. For very large files (>1GB), consider splitting into batches
- Change detection is O(n) where n is the total number of rows
- Database operations are batched and committed per change
- Consider indexing business key columns in Oracle for faster updates

---

## Future Enhancements

Potential improvements for future versions:
- [ ] Support for multiple CSV files
- [ ] Parallel processing for large datasets
- [ ] Support for other databases (SQL Server, PostgreSQL, MySQL)
- [ ] Incremental CSV loading (streaming)
- [ ] Web UI for configuration and monitoring
- [ ] Scheduled CDC runs (cron-like scheduler)
- [ ] Change notifications/alerts

---

## License & Support

For issues, questions, or contributions, please refer to your project documentation.

---

**Created**: 2024  
**Version**: 1.0  
**Status**: Production Ready

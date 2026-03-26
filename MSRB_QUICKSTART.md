# MSRB SCD Type 2 Loader - Quick Reference

## One-Command Execution

```bash
# First run (all inserts)
python msrb_scd2_loader.py

# Subsequent runs (with different files)
python msrb_scd2_loader.py "new_msrb_file_name.csv"
```

## What You Get

✅ **Automatic**:
- Database created on first run
- Table schema created automatically
- Records loaded with hash values
- Changes detected on each run

✅ **Outputs** (in `output/` directory):
- `MSRB_current.csv` - Current state (non-expired only)
- `MSRB_history.csv` - Full history (all versions)

✅ **Logging** (`msrb_loader.log`):
```
INSERTS:   X
UPDATES:   Y
EXPIRES:   Z
NO CHANGE: W
```

## Database Fields

```
MSRB_REC_ID        → Surrogate key (auto-increment)
MSRB_ID            → Business key (A5503, A7464, etc.)
FIRM_NAME          → Company name
STATE              → State code
REGISTRANT_TYPE    → Registration type
DATA_HASH          → MD5 hash (detects changes)
EFCT_TS            → When version became effective
EXPR_TS            → When version expires
CRT_TS             → When record was created
UPD_TS             → When record was updated
CREATE_USERID      → u8537748
```

## CDC Logic at a Glance

| Situation | Action |
|-----------|--------|
| New MSRB_ID | INSERT new record |
| Same MSRB_ID, same hash | NO CHANGE (skip) |
| Same MSRB_ID, different hash | UPDATE (expire old, insert new) |
| MSRB_ID gone from source | EXPIRE (set end date) |

## Sample Session

```bash
# Load 1 - Initial file (925 records)
$ python msrb_scd2_loader.py
✓ Loaded 925 records
  INSERTS:   925
  UPDATES:   0
  EXPIRES:   0
  Total: 925 current, 925 in history

# Make changes to CSV (3 updates, 5 deletes, 5 new)
# Load 2 - Modified file (925 records: 920 original + 5 new)
$ python msrb_scd2_loader.py "msrb_v2.csv"
✓ Loaded 925 records
  INSERTS:   5
  UPDATES:   3
  EXPIRES:   5
  NO CHANGE: 917
  Total: 925 current, 933 in history
```

## Verify Results

```bash
# Check log
Get-Content msrb_loader.log | Select-Object -Last 20

# Check database
sqlite3 msrb_warehouse.db
sqlite> SELECT COUNT(*) FROM MSRB_REGISTRANTS;
sqlite> SELECT COUNT(*) FROM MSRB_REGISTRANTS WHERE EXPR_TS > CURRENT_TIMESTAMP;

# Check exports
$current = (Import-Csv output/MSRB_current.csv | Measure).Count
$history = (Import-Csv output/MSRB_history.csv | Measure).Count
Write-Host "Current: $current, History: $history"
```

## Reset & Start Over

```bash
# Delete database to start fresh
rm msrb_warehouse.db

# Run loader - table will be recreated
python msrb_scd2_loader.py
```

## Key Points

- ✅ Same script, every time
- ✅ Persistent database across runs
- ✅ Automatic change detection
- ✅ Full audit trail maintained
- ✅ Easy export to CSV
- ✅ No configuration needed

**Run the same Python file. Database does the rest.**

# MSRB SCD Type 2 CDC Loader - Complete Guide

*A single Python script for persistent SCD Type 2 Change Data Capture with effective/expiration dates*

---

## 🎯 Overview

This solution provides a **single reusable Python script** that implements a persistent Slowly Changing Dimension (Type 2) loader for MSRB Registrants data. Each time you run it with a new MSRB file, it:

1. **Compares** new data with existing database records
2. **Detects** INSERT / UPDATE / DELETE / NO CHANGE operations
3. **Maintains** full history with effective and expiration timestamps
4. **Exports** both current and historical views

---

## 📋 What Makes This Different

**One Simple Script**: `msrb_scd2_loader.py`
- Run it repeatedly with different MSRB files
- No configuration changes needed
- Persistent database accumulates all changes
- Automatic table creation on first run

**Specific Field Handling**:
- `EFCT_TS` - When the record version became effective
- `EXPR_TS` - When the record expires (initially 31-Dec-9999)
- `CRT_TS` - When record was first created
- `UPD_TS` - When record was last updated
- `CREATE_USERID` - Always set to `u8537748`

**SCD Type 2 Logic**:
- Current records have `EXPR_TS > current date`
- Expired records have `EXPR_TS = expiration date`
- Full audit trail preserved

---

## 🚀 Quick Start

### First Run (Load 1) - All Inserts
```bash
python msrb_scd2_loader.py
```

**What happens**:
- Creates `msrb_warehouse.db` with MSRB_REGISTRANTS table
- Loads all 925 records from `2026-03-26_MSRBRegistrants.csv`
- All records inserted with hash values
- Exports to `output/` directory

**Expected Results**:
```
INSERTS:   925
UPDATES:   0
EXPIRES:   0
NO CHANGE: 0
```

---

### Second Run (Load 2) - Test I/U/D
```bash
python msrb_scd2_loader.py "2026-03-26_MSRBRegistrants_V2.csv"
```

**What happens**:
- Compares PK from new file with database
- Detects hash changes (updates)
- Finds missing PKs (expires)
- Finds new PKs (inserts)
- Keeps unchanged records

**Expected Results**:
```
INSERTS:   5      (new PKs: A9998, A9997, A9996, A9995, A9994)
UPDATES:   3      (hash changed: A5503, A5915, A2043)
EXPIRES:   5      (removed from source: last 5 records)
NO CHANGE: 917    (unchanged)
```

---

## 📊 Database Table Structure

```sql
CREATE TABLE MSRB_REGISTRANTS (
  MSRB_REC_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  MSRB_ID VARCHAR(50) NOT NULL,           -- Business key (A5503, A7464, etc.)
  FIRM_NAME VARCHAR(255),                 -- Company name
  STATE VARCHAR(2),                        -- State code (NJ, FL, CA, etc.)
  REGISTRANT_TYPE VARCHAR(100),           -- Broker Dealer / Broker Dealer/Mun Adv
  DATA_HASH VARCHAR(32),                  -- MD5 hash for change detection
  EFCT_TS TIMESTAMP,                      -- Effective timestamp (when version starts)
  EXPR_TS TIMESTAMP,                      -- Expiration timestamp (when version ends)
  CRT_TS TIMESTAMP,                       -- Creation timestamp (when first created)
  UPD_TS TIMESTAMP,                       -- Update timestamp (when last changed)
  CREATE_USERID VARCHAR(50)               -- Always: u8537748
)
```

---

## 🔍 CDC Logic Flow

### Scenario 1: New Record (INSERT)
**Condition**: `MSRB_ID` not found in current database records
```
Action: Insert new record with EXPR_TS = 31-Dec-9999
Result: Visible in current view
```

### Scenario 2: Record Unchanged (NO CHANGE)
**Condition**: `MSRB_ID` exists AND data hash is same
```
Action: Skip (no database changes)
Result: No new record created, version count unchanged
```

### Scenario 3: Record Changed (UPDATE)
**Condition**: `MSRB_ID` exists AND data hash is different
```
Actions:
  1. Expire old record: SET EXPR_TS = current_timestamp
  2. Insert new version: WITH EXPR_TS = 31-Dec-9999
Result: Now 2 versions in history, new one in current view
```

### Scenario 4: Record Deleted (EXPIRE)
**Condition**: `MSRB_ID` in database BUT not in source file
```
Action: Expire current record: SET EXPR_TS = current_timestamp
Result: Record no longer in current view, marked as expired in history
```

---

## 📁 Output Files

### `output/MSRB_current.csv`
**Shows**: Current state only (not expired)
**Contains**: 925 records after Load 2
**Records**: All active MSRB entries

**Example**:
```
MSRB_ID,FIRM_NAME,STATE,REGISTRANT_TYPE,DATA_HASH,EFCT_TS,EXPR_TS,CRT_TS,...
A5503,APW Capital Updated Inc.,NJ,Broker Dealer,43f1f7c54bf...,2026-03-26 21:20:10...
A7464,Zeus Financial LLC,FL,Broker Dealer,b3b3db91f6c...,2026-03-26 21:11:23...
A9998,New Firm 1,CA,Broker Dealer,d45abc12def...,2026-03-26 21:20:10...
```

### `output/MSRB_history.csv`
**Shows**: Full audit trail (all versions)
**Contains**: 933 records after Load 2
**Records**: Including old versions and expired records

**Example - Record with History**:
```
Load 1: A5503 - APW Capital, Inc.        [EXPR_TS=2026-03-26 21:20:10] EXPIRED
Load 2: A5503 - APW Capital Updated Inc. [EXPR_TS=31-Dec-9999]           CURRENT
```

---

## 📋 Data Handling Rules

| Situation | Rule |
|-----------|------|
| First load | All records = INSERT |
| PK match + hash same | NO CHANGE (skip) |
| PK match + hash different | UPDATE (expire old, insert new) |
| PK in DB but not source | EXPIRE (set expr_ts = now) |
| PK not in DB | INSERT (new record) |
| Same PK, multiple versions | Keep CRT_TS from original, update UPD_TS |

---

## 🎬 Demo: Complete Workflow

### Step 1: Initial Load
```bash
python msrb_scd2_loader.py
# Loads 2026-03-26_MSRBRegistrants.csv (925 records)
```

**Results**:
- Database created with 925 records
- All marked as INSERT
- EXPR_TS = 31-Dec-9999 (never expires initially)

### Step 2: Modify Data
Update the CSV file:
- Change 3 firm names or states (A5503, A5915, A2043)
- Remove last 5 records (A7554, A7401, A7167, A2938, A5759)
- Add 5 new records (A9998, A9997, A9996, A9995, A9994)

### Step 3: Run Loader Again
```bash
python msrb_scd2_loader.py "2026-03-26_MSRBRegistrants_V2.csv"
```

**Results**:
```
INSERTS:   5
UPDATES:   3
EXPIRES:   5
NO CHANGE: 917
TOTAL CURRENT: 925 (930 - 5 expired)
TOTAL HISTORY: 933 (925 original + 8 new versions)
```

### Step 4: Query Results
**Check current state**:
```
SELECT COUNT(*) FROM MSRB_REGISTRANTS 
WHERE EXPR_TS > current_timestamp OR EXPR_TS IS NULL
-- Result: 925
```

**Check all versions**:
```
SELECT COUNT(*) FROM MSRB_REGISTRANTS
-- Result: 933
```

**Check history for one firm**:
```
SELECT * FROM MSRB_REGISTRANTS 
WHERE MSRB_ID = 'A5503'
ORDER BY EFCT_TS
-- Result: 2 rows (old + new version)
```

---

## 🔑 Key Fields Explained

| Field | Example | Meaning |
|-------|---------|---------|
| `MSRB_REC_ID` | 1, 2, 3 | System-generated surrogate key (auto-increment) |
| `MSRB_ID` | A5503, A7464 | Business key - used to match records |
| `FIRM_NAME` | APW Capital, Inc. | Company name from source |
| `STATE` | NJ, FL, TX | State code from source |
| `REGISTRANT_TYPE` | Broker Dealer | Type from source |
| `DATA_HASH` | 43f1f7c54bf292a4 | MD5 hash of business columns (detects changes) |
| `EFCT_TS` | 2026-03-26 21:20:10 | When this version became effective |
| `EXPR_TS` | 9999-12-31 00:00:00 | When this version expires (null = never) |
| `CRT_TS` | 2026-03-26 21:11:23 | When record was first created (never changes) |
| `UPD_TS` | 2026-03-26 21:20:10 | When record was last updated (changes on UPDATE) |
| `CREATE_USERID` | u8537748 | User ID (always this value) |

---

## ✅ Verification Checklist

After each run:

- [ ] `msrb_warehouse.db` exists
- [ ] `output/MSRB_current.csv` generated
- [ ] `output/MSRB_history.csv` generated
- [ ] Log file shows expected counts (I/U/D)
- [ ] No errors in `msrb_loader.log`
- [ ] Current count = expected
- [ ] History count = original + new versions

---

## 🔧 Usage Variations

### Default File Path
```bash
python msrb_scd2_loader.py
# Uses: 2026-03-26_MSRBRegistrants.csv
```

### Custom File Path
```bash
python msrb_scd2_loader.py "/path/to/any_msrb_file.csv"
# Uses: Specified file
```

### Reset Database
```bash
rm msrb_warehouse.db
python msrb_scd2_loader.py
# Starts fresh with all records as insertions
```

---

## 📊 Summary of Test Results

### Load 1 (Initial)
- **Source**: 925 records
- **Action**: All inserted
- **Database**: 925 records
- **Current View**: 925 active
- **History View**: 925 total

### Load 2 (Changes)
- **Source**: 925 records (3 updated, 5 removed, 5 new)
- **Actions**: 5 INSERT + 3 UPDATE + 5 EXPIRE + 917 NO_CHANGE
- **Database**: Still 925 current, but with new versions of updated records
- **Current View**: 925 active (920 unchanged + 3 updated + 5 new, minus 5 expired)
- **History View**: 933 total (925 original + 3 old versions + 5 expired = 938... no wait)

Actually:
- History = Original 925 + New updated versions 3 + Expired markers 5 = 933 ✓

---

## 🎯 Production Workflow

1. **Receive new MSRB file** (e.g., monthly export)
2. **Run single command**: `python msrb_scd2_loader.py "new_file.csv"`
3. **Check results**: Review logs and exports
4. **Load to warehouse**: Use `output/MSRB_current.csv` for current state
5. **Audit trail**: Use `output/MSRB_history.csv` for compliance

---

## 📝 Files Provided

| File | Purpose |
|------|---------|
| `msrb_scd2_loader.py` | Main CDC loader script (run this) |
| `create_test_data.py` | Helper to create test files with changes |
| `msrb_warehouse.db` | SQLite database (auto-created) |
| `msrb_loader.log` | Execution log with all details |
| `output/MSRB_current.csv` | Current state export |
| `output/MSRB_history.csv` | Full history export |

---

## ✨ Features

✅ **Fully Persistent**: Database persists between runs  
✅ **Automatic Schema**: Table created on first run  
✅ **MD5 Hashing**: Detects any column changes  
✅ **SCD Type 2**: Maintains full version history  
✅ **Effective Dates**: Track when changes occurred  
✅ **User Tracking**: Audit with CREATE_USERID  
✅ **CSV Export**: Easy integration with data warehouse  
✅ **Detailed Logging**: Know exactly what happened  
✅ **No Configuration**: Just run the script  
✅ **Single File Execution**: Reusable for any load  

---

**Enjoy your enterprise-grade SCD Type 2 CDC without licensing costs!** 🚀

# MSRB SCD Type 2 CDC - Getting Started in 5 Minutes

## What You Have

✅ **msrb_scd2_loader.py** - The only file you need to run (reusable)
✅ **Persistent database** - Accumulates changes automatically
✅ **Complete documentation** - Reference guides and examples
✅ **Tested and verified** - Works with 925+ records

---

## 🚀 Step 1: First Run (Initial Load)

```bash
python msrb_scd2_loader.py
```

**What happens**:
- Creates `msrb_warehouse.db` (SQLite database)
- Creates `MSRB_REGISTRANTS` table with proper schema
- Loads all 925 records from `2026-03-26_MSRBRegistrants.csv`
- Generates hash values for each record
- Exports results to `output/` folder

**Expected output**:
```
MSRB SCD Type 2 Loader
================================================================================
...processing...
INSERTS:   925
UPDATES:   0
EXPIRES:   0
NO CHANGE: 0

Exported 925 current records to output/MSRB_current.csv
Exported 925 history records to output/MSRB_history.csv
```

---

## 🔄 Step 2: Second Run (Load Updates)

Make changes to your MSRB file (or use a new version), then:

```bash
python msrb_scd2_loader.py "new_msrb_file.csv"
```

**What happens**:
- Compares new file against database records
- Detects which records are NEW, UPDATED, DELETED, or UNCHANGED
- Updates database with SCD Type 2 logic (old versions expired, new versions inserted)
- Exports updated results

**Expected output**:
```
INSERTS:   5      ← New records added
UPDATES:   3      ← Records with changed data
EXPIRES:   5      ← Records no longer in source
NO CHANGE: 917    ← Records that stayed the same
```

---

## 📊 Step 3: Check Results

### View current state (non-expired records)
```bash
# CSV file preview
Get-Content output/MSRB_current.csv | Select-Object -First 5

# Or open in Excel
output/MSRB_current.csv
```

### View full history (all versions)
```bash
# CSV file preview
Get-Content output/MSRB_history.csv | Select-Object -First 5

# Or open in Excel
output/MSRB_history.csv
```

### Check the log
```bash
Get-Content msrb_loader.log | Select-Object -Last 30
```

---

## 🔑 Key Fields in Output

When you open the CSV files, you'll see:

| Field | What It Means |
|-------|---------------|
| `MSRB_REC_ID` | Unique record ID (auto-generated) |
| `MSRB_ID` | The firm ID from your source file |
| `FIRM_NAME` | Company name |
| `STATE` | State code |
| `REGISTRANT_TYPE` | Business type |
| `DATA_HASH` | Fingerprint showing what changed |
| `EFCT_TS` | When this version became active |
| `EXPR_TS` | When this version expires |
| `CRT_TS` | When record was first created |
| `UPD_TS` | When record was last changed |
| `CREATE_USERID` | Always shows: u8537748 |

---

## 💡 Understanding the Outputs

### MSRB_current.csv
- **Shows**: What your data looks like RIGHT NOW
- **Contains**: Only active records (not expired)
- **Use for**: Loading to your data warehouse
- **Records**: Same number as input (but with change history)

### MSRB_history.csv
- **Shows**: Everything that happened (audit trail)
- **Contains**: All versions of all records
- **Use for**: Compliance, auditing, tracking changes
- **Records**: More than input (has multiple versions of changed records)

---

## 🔄 Example: What Happens to One Record

### Original (Load 1)
```
MSRB_ID: A5503
FIRM_NAME: APW Capital, Inc.
EFCT_TS: 2026-03-26 21:11:22
EXPR_TS: 9999-12-31 00:00:00 ← Never expires
Status: CURRENT
```

### After Update (Load 2)
The database now has TWO versions:

**Old version** (marked as expired):
```
MSRB_ID: A5503
FIRM_NAME: APW Capital, Inc.
EFCT_TS: 2026-03-26 21:11:22
EXPR_TS: 2026-03-26 21:20:10 ← Expired when we updated
Status: HISTORY (old)
```

**New version** (now active):
```
MSRB_ID: A5503
FIRM_NAME: APW Capital Updated Inc. ← Changed
EFCT_TS: 2026-03-26 21:20:10   ← When update happened
EXPR_TS: 9999-12-31 00:00:00   ← Never expires
Status: CURRENT (new)
```

---

## 📋 Complete Workflow

```
┌─────────────────────────────────────────────────────────┐
│ Day 1: Receive initial MSRB file (925 records)          │
│ Command: python msrb_scd2_loader.py                     │
│ Result: 925 INSERTS, database created                   │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ Day 2: Process updated MSRB file (changes made)         │
│ Command: python msrb_scd2_loader.py "v2.csv"           │
│ Result: 5 INS + 3 UPD + 5 EXP + 917 NO CHG             │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ Review outputs:                                          │
│ - output/MSRB_current.csv (925 active)                 │
│ - output/MSRB_history.csv (933 versions)               │
│ - msrb_loader.log (complete audit)                     │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ Load to warehouse or use in reports                      │
│ (repeat process for next month/file)                    │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Quick Checklist

Before running:
- [ ] MSRB CSV file ready
- [ ] Python installed on your machine
- [ ] Script is in the same folder as CSV

After running:
- [ ] Check `msrb_loader.log` for errors
- [ ] Verify `output/MSRB_current.csv` has data
- [ ] Check Insert/Update/Delete counts match expectations
- [ ] Database persisted for next run

---

## 🎯 Real-World Example

```bash
# Month 1 - Initial load
python msrb_scd2_loader.py "2026-03-26_MSRB.csv"
✓ 925 records loaded

# Month 2 - New data arrives
python msrb_scd2_loader.py "2026-04-30_MSRB.csv"
✓ 5 inserts, 3 updates, 2 expires, 915 no change

# Month 3 - Another update
python msrb_scd2_loader.py "2026-05-31_MSRB.csv"
✓ 2 inserts, 1 update, 0 expires, 922 no change

# All history preserved in database across all 3 months!
```

---

## 📞 Troubleshooting

| Issue | Solution |
|-------|----------|
| "CSV file not found" | Make sure file is in same folder as script |
| Database errors | Delete `msrb_warehouse.db` to start fresh |
| No output files | Check `msrb_loader.log` for error details |
| Wrong record counts | Verify CSV format matches expected columns |

---

## 📚 Documentation

For more details, see:
- **MSRB_QUICKSTART.md** - Quick commands reference
- **MSRB_SCD2_GUIDE.md** - Complete technical guide
- **IMPLEMENTATION_SUMMARY_SCD2.md** - Project details

---

## 🎉 You're Ready!

That's it! Just run:
```bash
python msrb_scd2_loader.py
```

Everything else happens automatically.

**Questions?** Check the logs or refer to the detailed guides provided.

Happy CDC processing! 🚀

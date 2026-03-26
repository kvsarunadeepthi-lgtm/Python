import pandas as pd

# Load the original file
df = pd.read_csv('2026-03-26_MSRBRegistrants.csv')

# Create a modified version for testing CDC logic
# Keep first 920 records
df_modified = df.iloc[0:920].copy()

# Update 3 records (change firm name or registrant type)
df_modified.loc[0, 'Firm Name'] = 'APW Capital Updated Inc.'
df_modified.loc[5, 'Registrant Type'] = 'Broker Dealer/Municipal Advisor'
df_modified.loc[10, 'State'] = 'TX'

# Add 5 new records
new_records = pd.DataFrame({
    'Firm Name': ['New Firm 1', 'New Firm 2', 'New Firm 3', 'New Firm 4', 'New Firm 5'],
    'MSRB ID': ['A9998', 'A9997', 'A9996', 'A9995', 'A9994'],
    'State': ['CA', 'NY', 'TX', 'FL', 'IL'],
    'Registrant Type': ['Broker Dealer', 'Broker Dealer', 'Broker Dealer/Municipal Advisor', 'Broker Dealer', 'Broker Dealer']
})

df_modified = pd.concat([df_modified, new_records], ignore_index=True)

# Save as new file (this removes 5 records: rows 920-924, adds 5 new ones)
df_modified.to_csv('2026-03-26_MSRBRegistrants_V2.csv', index=False)
print(f"Created modified MSRB file with {len(df_modified)} records")
print(f"Changes: 3 updates (rows 0, 5, 10), 5 deletes (PK A5759-A2938), 5 new inserts (A9998-A9994)")

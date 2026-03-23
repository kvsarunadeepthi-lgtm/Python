"""
CDC Framework Example Usage
Demonstrates how to use the CDC framework for Change Data Capture
"""

import logging
from cdc_config import CDCConfigLoader
from cdc_engine import CDCEngine
from db_connector import OracleConnector

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function demonstrating CDC framework usage"""
    
    print("=" * 70)
    print("CDC FRAMEWORK - CHANGE DATA CAPTURE EXAMPLE")
    print("=" * 70)
    
    # Step 1: Load configuration from JSON
    print("\n[Step 1] Loading CDC Configuration...")
    try:
        config = CDCConfigLoader.load_config('cdc_config_example.json')
        CDCConfigLoader.validate_config(config)
        print(f"✓ Configuration loaded successfully for table: {config.table_name}")
        print(f"  - Oracle Table: {config.oracle_table_name}")
        print(f"  - Source File: {config.source_file_path}")
        print(f"  - Business Keys: {config.business_keys}")
        print(f"  - Total Columns: {len(config.columns)}")
    except Exception as e:
        print(f"✗ Failed to load configuration: {str(e)}")
        return
    
    # Step 2: Initialize Database Connector
    print("\n[Step 2] Initializing Oracle Database Connector...")
    
    # *** IMPORTANT: Configure your Oracle connection details here ***
    ORACLE_CONNECTION_STRING = "localhost:1521/ORCL"  # Update with your connection string
    ORACLE_USERNAME = "your_username"                  # Update with your username
    ORACLE_PASSWORD = "your_password"                  # Update with your password
    
    db_connector = OracleConnector(
        connection_string=ORACLE_CONNECTION_STRING,
        username=ORACLE_USERNAME,
        password=ORACLE_PASSWORD
    )
    
    print(f"✓ Database connector initialized")
    print(f"  - Connection String: {ORACLE_CONNECTION_STRING}")
    
    # Step 3: Initialize CDC Engine
    print("\n[Step 3] Initializing CDC Engine...")
    cdc_engine = CDCEngine(
        config=config,
        db_connector=db_connector,
        snapshot_file=f".cdc_{config.table_name}_snapshot.json"
    )
    print("✓ CDC Engine initialized")
    
    # Step 4: Run CDC Process
    print("\n[Step 4] Running CDC Process...")
    print("-" * 70)
    
    success = cdc_engine.run()
    
    print("-" * 70)
    
    if success:
        print("\n✓ CDC Process Completed Successfully!")
        
        # Step 5: Display Summary
        print("\n[Step 5] Change Summary:")
        summary = cdc_engine.get_change_summary()
        print(f"  - Total Changes: {summary['total']}")
        print(f"  - Inserts: {summary['inserts']}")
        print(f"  - Updates: {summary['updates']}")
        print(f"  - Deletes: {summary['deletes']}")
    else:
        print("\n✗ CDC Process Failed!")
        print("Please check the logs above for details.")
    
    print("\n" + "=" * 70)


def example_with_test_data():
    """
    Example showing CDC process with test data
    This creates sample snapshots for testing without a real database
    """
    print("\n" + "=" * 70)
    print("TEST MODE - Using Sample Data (No Database Required)")
    print("=" * 70)
    
    import json
    from pathlib import Path
    
    # Step 1: Load configuration
    print("\n[Step 1] Loading Configuration...")
    config = CDCConfigLoader.load_config('cdc_config_example.json')
    CDCConfigLoader.validate_config(config)
    print(f"✓ Configuration loaded for table: {config.table_name}")
    
    # Step 2: Create initial snapshot
    print("\n[Step 2] Creating Initial Snapshot...")
    initial_data = {
        "0": {"CUSTOMER_ID": "1", "CUSTOMER_NAME": "John Smith", "EMAIL": "john.smith@email.com", 
              "PHONE": "555-0001", "ADDRESS": "123 Main St", "CITY": "New York", "STATUS": "ACTIVE"},
        "1": {"CUSTOMER_ID": "2", "CUSTOMER_NAME": "Jane Doe", "EMAIL": "jane.doe@email.com", 
              "PHONE": "555-0002", "ADDRESS": "456 Oak Ave", "CITY": "Los Angeles", "STATUS": "ACTIVE"},
        "2": {"CUSTOMER_ID": "3", "CUSTOMER_NAME": "Bob Johnson", "EMAIL": "bob.johnson@email.com", 
              "PHONE": "555-0003", "ADDRESS": "789 Pine Rd", "CITY": "Chicago", "STATUS": "ACTIVE"}
    }
    
    snapshot_file = f".cdc_{config.table_name}_snapshot.json"
    with open(snapshot_file, 'w') as f:
        json.dump(initial_data, f, indent=2)
    print(f"✓ Initial snapshot created with {len(initial_data)} records")
    
    # Step 3: Simulate updated data with changes
    print("\n[Step 3] Simulating Data Changes...")
    updated_data = {
        "0": {"CUSTOMER_ID": "1", "CUSTOMER_NAME": "John Smith UPDATED", "EMAIL": "john.new@email.com", 
              "PHONE": "555-0001", "ADDRESS": "123 Main St", "CITY": "New York", "STATUS": "ACTIVE"},  # Updated
        "1": {"CUSTOMER_ID": "2", "CUSTOMER_NAME": "Jane Doe", "EMAIL": "jane.doe@email.com", 
              "PHONE": "555-0002", "ADDRESS": "456 Oak Ave", "CITY": "Los Angeles", "STATUS": "ACTIVE"},  # No change
        "3": {"CUSTOMER_ID": "4", "CUSTOMER_NAME": "Alice Williams", "EMAIL": "alice.williams@email.com", 
              "PHONE": "555-0004", "ADDRESS": "321 Elm St", "CITY": "Houston", "STATUS": "ACTIVE"}  # New record
        # Record 3 (Bob Johnson) is deleted
    }
    
    # Create temporary CSV with updated data
    csv_file = "temp_customers_updated.csv"
    with open(csv_file, 'w') as f:
        f.write("CUSTOMER_ID,CUSTOMER_NAME,EMAIL,PHONE,ADDRESS,CITY,STATUS\n")
        for row in updated_data.values():
            f.write(f"{row['CUSTOMER_ID']},{row['CUSTOMER_NAME']},{row['EMAIL']},{row['PHONE']},{row['ADDRESS']},{row['CITY']},{row['STATUS']}\n")
    
    print(f"✓ Test data created with changes:")
    print(f"  - 1 Record Updated (John Smith)")
    print(f"  - 1 Record Unchanged (Jane Doe)")
    print(f"  - 1 Record Inserted (Alice Williams)")
    print(f"  - 1 Record Deleted (Bob Johnson)")
    
    # Step 4: Demonstrate change detection
    print("\n[Step 4] Change Detection (Without Database)...")
    from change_tracker import ChangeTracker
    
    # Convert snapshots to proper format
    old_data_dict = {int(k): v for k, v in initial_data.items()}
    new_data_dict = {int(k): v for k, v in updated_data.items()}
    
    tracker = ChangeTracker(config.business_keys)
    changes = tracker.detect_changes(old_data_dict, new_data_dict)
    tracker.print_summary()
    
    # Step 5: Print detailed changes
    print("\n[Step 5] Detailed Change Analysis:")
    for change in changes:
        print(f"\n  {change.change_type.value}:")
        print(f"    - Business Key: {change.business_keys}")
        if change.change_type.value == "UPDATE":
            print(f"    - Changed Columns: {change.changed_columns}")
            for col in change.changed_columns:
                print(f"      • {col}: '{change.old_values.get(col)}' → '{change.new_values.get(col)}'")
    
    # Cleanup
    Path(snapshot_file).unlink(missing_ok=True)
    Path(csv_file).unlink(missing_ok=True)
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Uncomment the appropriate example to run
    
    # Run with actual Oracle database (requires configuration)
    # main()
    
    # Run test mode with sample data (no database required)
    example_with_test_data()

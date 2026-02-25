#!/usr/bin/env python3
"""
Quick Start Guide - Oracle Database Connection
This demonstrates how to test and use Oracle with the metadata loader
"""

import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_oracle_connection(username: str, password: str, dsn: str) -> bool:
    """Test if oracledb is installed and connection works"""
    
    try:
        import oracledb
        logger.info("✓ oracledb module found")
        
        logger.info(f"Testing connection to: {dsn}")
        conn = oracledb.connect(
            user=username,
            password=password,
            dsn=dsn
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        logger.info("✓ Successfully connected to Oracle!")
        return True
        
    except ImportError:
        logger.error("✗ oracledb not installed")
        logger.info("Install with: pip install oracledb")
        return False
    except Exception as e:
        logger.error(f"✗ Connection failed: {str(e)}")
        return False


def print_oracle_checklist():
    """Print Oracle setup checklist"""
    
    print("\n" + "=" * 60)
    print("ORACLE DATABASE SETUP CHECKLIST")
    print("=" * 60)
    
    checklist = [
        "Install oracledb: pip install oracledb",
        "Have Oracle Database running and accessible",
        "Obtain connection details:",
        "  - Hostname (or IP address)",
        "  - Port (default: 1521)",
        "  - Service Name or SID (e.g., ORCL)",
        "  - Username (e.g., hr)",
        "  - Password",
        "Test connection using this script",
        "Update oracle_config in your Python code",
        "Run metadata_loader with Oracle target"
    ]
    
    for i, item in enumerate(checklist, 1):
        print(f"{i:2d}. {item}")
    
    print("\n" + "=" * 60)


def print_oracle_config_template():
    """Print Oracle configuration template"""
    
    print("\n" + "=" * 60)
    print("ORACLE CONFIGURATION TEMPLATE")
    print("=" * 60)
    
    template = """
# Copy and paste into your Python script:

oracle_config = {
    'username': 'your_oracle_user',
    'password': 'your_oracle_password',
    'dsn': 'hostname:1521/service_name'
}

# Example:
oracle_config = {
    'username': 'hr',
    'password': 'abc123',
    'dsn': 'localhost:1521/ORCL'
}

# Then use with MetadataBasedDataLoader:
loader = MetadataBasedDataLoader(
    metadata_file='sttm.json',
    csv_file='emp.csv',
    oracle_config=oracle_config
)

success = loader.run_pipeline(
    csv_file='emp.csv',
    output_formats=['csv', 'json', 'oracle']
)
"""
    
    print(template)
    print("=" * 60)


def print_dsn_examples():
    """Print DSN format examples"""
    
    print("\n" + "=" * 60)
    print("DATA SOURCE NAME (DSN) EXAMPLES")
    print("=" * 60)
    
    examples = {
        "Local Oracle": "localhost:1521/ORCL",
        "Remote Oracle": "db-server.example.com:1521/PROD",
        "IP Address": "192.168.1.100:1521/ORCL",
        "Non-standard Port": "oracle-host:1526/SERVICE",
        "Docker Container": "oracle-container:1521/ORCLPDB1",
        "Cloud (AWS RDS)": "orcl.xxx.rds.amazonaws.com:1521/ORCL",
        "Cloud (Azure)": "orcl.xxx.database.azure.com:1521/ORCL"
    }
    
    for env, dsn in examples.items():
        print(f"{env:.<30} {dsn}")
    
    print("=" * 60)


def print_common_errors():
    """Print common errors and solutions"""
    
    print("\n" + "=" * 60)
    print("COMMON ERRORS & SOLUTIONS")
    print("=" * 60)
    
    errors = {
        "ModuleNotFoundError: No module named 'oracledb'": 
            "Solution: pip install oracledb",
        
        "ORA-01017: invalid username/password; logon denied":
            "Solution: Check username and password in oracle_config",
        
        "ORA-12514: TNS:listener does not currently know of service":
            "Solution: Verify service name in DSN (use correct SID or service)",
        
        "ORA-12545: Connect failed because target host or object does not exist":
            "Solution: Check hostname and port in DSN",
        
        "ORA-01400: cannot insert NULL into table":
            "Solution: Add missing columns to CSV or set 'is Null': 'Y' in metadata",
        
        "ORA-00942: table or view does not exist":
            "Solution: Verify table name and schema permissions",
        
        "Connection timeout":
            "Solution: Check firewall, network connectivity, and Oracle listener status"
    }
    
    for error, solution in errors.items():
        print(f"\nError: {error}")
        print(f"{solution}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_oracle_checklist()
    print_dsn_examples()
    print_oracle_config_template()
    print_common_errors()
    
    # Test connection if credentials provided
    print("\n" + "=" * 60)
    print("TESTING ORACLE CONNECTION")
    print("=" * 60)
    
    # Example: Uncomment and fill in actual credentials to test
    # test_oracle_connection(
    #     username='your_user',
    #     password='your_password',
    #     dsn='your_host:1521/your_service'
    # )
    
    print("\nTo test your Oracle connection:")
    print("1. Edit this script and uncomment test_oracle_connection()")
    print("2. Add your actual Oracle credentials")
    print("3. Run: python oracle_quick_start.py")
    print("\n" + "=" * 60)

"""
Simplified SCD Type 2 CDC Loader for MSRB Registrants
Single script to run repeatedly with new MSRB files
Maintains persistent database with effective/expiration dates
"""

import pandas as pd
import sqlite3
import hashlib
import sys
from datetime import datetime, date
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('msrb_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = 'msrb_warehouse.db'
TABLE_NAME = 'MSRB_REGISTRANTS'
DEFAULT_USERID = 'u8537748'
HIGH_END_DATE = datetime(9999, 12, 31, 0, 0, 0)  # 31-Dec-9999 12:00:00 AM
PK_COLUMN = 'MSRB_ID'  # Primary/Business Key (in database)
SOURCE_PK_COLUMN = 'MSRB ID'  # Primary/Business Key (in CSV file, with space)


class MSRBSCDLoader:
    """SCD Type 2 Loader for MSRB Registrants"""
    
    def __init__(self, db_file: str = DB_FILE):
        """Initialize database connection"""
        self.db_file = db_file
        self.connection = self._connect_db()
        self._create_table()
        logger.info(f"Connected to database: {db_file}")
    
    def _connect_db(self) -> sqlite3.Connection:
        """Create database connection"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_table(self):
        """Create MSRB_REGISTRANTS table if it doesn't exist"""
        cursor = self.connection.cursor()
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            MSRB_REC_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            {PK_COLUMN} VARCHAR(50) NOT NULL,
            FIRM_NAME VARCHAR(255),
            STATE VARCHAR(2),
            REGISTRANT_TYPE VARCHAR(100),
            DATA_HASH VARCHAR(32),
            EFCT_TS TIMESTAMP,
            EXPR_TS TIMESTAMP,
            CRT_TS TIMESTAMP,
            UPD_TS TIMESTAMP,
            CREATE_USERID VARCHAR(50)
        )
        """
        
        cursor.execute(create_sql)
        self.connection.commit()
        logger.info(f"Table {TABLE_NAME} ready")
    
    def _generate_hash(self, row_dict: dict) -> str:
        """Generate MD5 hash for row data (excluding metadata fields)"""
        # Include only business columns in hash (use source column names from CSV)
        cols_to_hash = [SOURCE_PK_COLUMN, 'Firm Name', 'State', 'Registrant Type']
        hash_input = ''.join(str(row_dict.get(col, '')) for col in cols_to_hash)
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _load_csv(self, csv_file: str) -> pd.DataFrame:
        """Load MSRB CSV file"""
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} records from {csv_file}")
        return df
    
    def _get_current_records(self) -> dict:
        """Get all current records (not expired)"""
        cursor = self.connection.cursor()
        
        sql = f"""
        SELECT * FROM {TABLE_NAME}
        WHERE EXPR_TS > ? OR EXPR_TS IS NULL
        """
        
        cursor.execute(sql, (datetime.now(),))
        rows = cursor.fetchall()
        
        # Create dictionary keyed by business key
        records = {}
        for row in rows:
            pk_value = row[PK_COLUMN]
            records[pk_value] = dict(row)
        
        return records
    
    def process_load(self, csv_file: str) -> dict:
        """
        Main CDC processing logic
        
        Returns:
            Dictionary with counts: inserts, updates, deletes
        """
        logger.info("\n" + "="*80)
        logger.info("Starting MSRB SCD Type 2 Load")
        logger.info("="*80)
        
        # Load source data
        source_df = self._load_csv(csv_file)
        source_df = source_df.fillna('')  # Replace NaN with empty string
        
        # Get current records from database
        current_records = self._get_current_records()
        
        insert_count = 0
        update_count = 0
        expire_count = 0
        no_change_count = 0
        
        now = datetime.now()
        today = date.today()
        cursor = self.connection.cursor()
        
        # Track which PKs were processed
        processed_pks = set()
        
        logger.info(f"\nProcessing {len(source_df)} source records...")
        
        # Process each source record
        for idx, source_row in source_df.iterrows():
            try:
                pk_value = source_row.get(SOURCE_PK_COLUMN, '').strip()
                if not pk_value:
                    logger.warning(f"Row {idx}: Missing {SOURCE_PK_COLUMN}, skipping")
                    continue
                
                processed_pks.add(pk_value)
                
                # Generate hash for new record
                new_hash = self._generate_hash(source_row.to_dict())
                
                if pk_value not in current_records:
                    # INSERT - new record not in database
                    insert_count += 1
                    logger.info(f"  INSERT: {pk_value}")
                    
                    insert_sql = f"""
                    INSERT INTO {TABLE_NAME} 
                    ({PK_COLUMN}, FIRM_NAME, STATE, REGISTRANT_TYPE, DATA_HASH, 
                     EFCT_TS, EXPR_TS, CRT_TS, UPD_TS, CREATE_USERID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    cursor.execute(insert_sql, (
                        pk_value,
                        source_row.get('Firm Name', ''),
                        source_row.get('State', ''),
                        source_row.get('Registrant Type', ''),
                        new_hash,
                        now,
                        HIGH_END_DATE,
                        now,
                        now,
                        DEFAULT_USERID
                    ))
                
                else:
                    # Record exists - check if hash is different
                    existing_record = current_records[pk_value]
                    existing_hash = existing_record.get('DATA_HASH')
                    
                    if existing_hash != new_hash:
                        # UPDATE - record exists but data changed
                        update_count += 1
                        logger.info(f"  UPDATE: {pk_value}")
                        
                        # Expire old record
                        expire_sql = f"""
                        UPDATE {TABLE_NAME}
                        SET EXPR_TS = ?
                        WHERE {PK_COLUMN} = ? AND (EXPR_TS > ? OR EXPR_TS IS NULL)
                        """
                        cursor.execute(expire_sql, (now, pk_value, now))
                        
                        # Insert new version
                        insert_sql = f"""
                        INSERT INTO {TABLE_NAME}
                        ({PK_COLUMN}, FIRM_NAME, STATE, REGISTRANT_TYPE, DATA_HASH,
                         EFCT_TS, EXPR_TS, CRT_TS, UPD_TS, CREATE_USERID)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        
                        cursor.execute(insert_sql, (
                            pk_value,
                            source_row.get('Firm Name', ''),
                            source_row.get('State', ''),
                            source_row.get('Registrant Type', ''),
                            new_hash,
                            now,
                            HIGH_END_DATE,
                            existing_record['CRT_TS'],  # Keep original creation timestamp
                            now,
                            DEFAULT_USERID
                        ))
                    else:
                        # NO CHANGE - record exists and data is same
                        no_change_count += 1
                        logger.debug(f"  NO CHANGE: {pk_value}")
            
            except Exception as e:
                logger.error(f"Error processing row {idx}: {str(e)}")
                continue
        
        # EXPIRE records - PKs in database but not in source
        logger.info(f"\nDetecting EXPIRE records...")
        for pk_value, existing_record in current_records.items():
            expr_ts = existing_record.get('EXPR_TS')
            # Convert to datetime if it's a string
            if isinstance(expr_ts, str):
                expr_ts = datetime.fromisoformat(expr_ts)
            
            if pk_value not in processed_pks and (expr_ts is None or expr_ts > now):
                # Record exists in database but not in source - expire it
                expire_count += 1
                logger.info(f"  EXPIRE: {pk_value}")
                
                expire_sql = f"""
                UPDATE {TABLE_NAME}
                SET EXPR_TS = ?
                WHERE {PK_COLUMN} = ? AND (EXPR_TS > ? OR EXPR_TS IS NULL)
                """
                cursor.execute(expire_sql, (now, pk_value, now))
        
        self.connection.commit()
        
        # Log summary
        logger.info(f"\n{'='*80}")
        logger.info(f"MSRB SCD Type 2 Load Summary")
        logger.info(f"{'='*80}")
        logger.info(f"INSERTS:   {insert_count}")
        logger.info(f"UPDATES:   {update_count}")
        logger.info(f"EXPIRES:   {expire_count}")
        logger.info(f"NO CHANGE: {no_change_count}")
        logger.info(f"{'='*80}\n")
        
        return {
            'inserts': insert_count,
            'updates': update_count,
            'expires': expire_count,
            'no_change': no_change_count,
            'total': len(source_df)
        }
    
    def get_current_view(self) -> pd.DataFrame:
        """Get current view (non-expired records only)"""
        sql = f"""
        SELECT 
            MSRB_REC_ID,
            {PK_COLUMN},
            FIRM_NAME,
            STATE,
            REGISTRANT_TYPE,
            DATA_HASH,
            EFCT_TS,
            EXPR_TS,
            CRT_TS,
            UPD_TS,
            CREATE_USERID
        FROM {TABLE_NAME}
        WHERE EXPR_TS > ? OR EXPR_TS IS NULL
        ORDER BY {PK_COLUMN}
        """
        
        df = pd.read_sql_query(sql, self.connection, params=(datetime.now(),))
        return df
    
    def get_full_history(self) -> pd.DataFrame:
        """Get full history (all records including expired)"""
        sql = f"""
        SELECT 
            MSRB_REC_ID,
            {PK_COLUMN},
            FIRM_NAME,
            STATE,
            REGISTRANT_TYPE,
            DATA_HASH,
            EFCT_TS,
            EXPR_TS,
            CRT_TS,
            UPD_TS,
            CREATE_USERID
        FROM {TABLE_NAME}
        ORDER BY {PK_COLUMN}, EFCT_TS
        """
        
        df = pd.read_sql_query(sql, self.connection)
        return df
    
    def export_current(self, output_file: str):
        """Export current view to CSV"""
        df = self.get_current_view()
        df.to_csv(output_file, index=False)
        logger.info(f"Exported {len(df)} current records to {output_file}")
        return df
    
    def export_history(self, output_file: str):
        """Export full history to CSV"""
        df = self.get_full_history()
        df.to_csv(output_file, index=False)
        logger.info(f"Exported {len(df)} history records to {output_file}")
        return df
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


def main():
    """Main execution function"""
    
    print("\n" + "="*80)
    print("MSRB SCD Type 2 Loader")
    print("="*80)
    
    # Determine input file
    script_dir = Path(__file__).parent
    
    if len(sys.argv) > 1:
        # Use provided file path
        csv_file = sys.argv[1]
    else:
        # Use default MSRB file
        csv_file = str(script_dir / '2026-03-26_MSRBRegistrants.csv')
    
    if not Path(csv_file).exists():
        print(f"\nError: File not found: {csv_file}")
        print(f"Usage: python msrb_scd2_loader.py [path_to_csv_file]")
        sys.exit(1)
    
    try:
        # Initialize loader
        loader = MSRBSCDLoader(str(script_dir / DB_FILE))
        
        # Process the load
        result = loader.process_load(csv_file)
        
        # Show current records
        print(f"\n[Current Records (Non-Expired Only)]")
        print("="*80)
        current = loader.get_current_view()
        print(f"Total current records: {len(current)}\n")
        print(current[['MSRB_ID', 'FIRM_NAME', 'STATE', 'EFCT_TS', 'EXPR_TS']].to_string(index=False))
        
        # Export results
        print(f"\n[Exporting Results]")
        print("="*80)
        
        output_dir = script_dir / 'output'
        output_dir.mkdir(exist_ok=True)
        
        current_file = str(output_dir / 'MSRB_current.csv')
        history_file = str(output_dir / 'MSRB_history.csv')
        
        loader.export_current(current_file)
        loader.export_history(history_file)
        
        loader.close()
        
        print("\n" + "="*80)
        print("MSRB Load Complete")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

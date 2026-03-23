"""
CDC Engine - Main orchestration module
Coordinates CSV reading, change detection, and database updates
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from datetime import datetime
import json

from cdc_config import TableConfig, CDCConfigLoader, ColumnConfig
from db_connector import OracleConnector
from change_tracker import ChangeTracker, ChangeType, ChangeRecord

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CDCEngine:
    """Main CDC Engine that orchestrates the entire CDC process"""
    
    def __init__(self, config: TableConfig, db_connector: OracleConnector,
                 snapshot_file: Optional[str] = None):
        """
        Initialize CDC Engine
        
        Args:
            config: TableConfig object
            db_connector: OracleConnector for database operations
            snapshot_file: Path to store previous snapshot (for comparison)
        """
        self.config = config
        self.db_connector = db_connector
        self.snapshot_file = snapshot_file or f".cdc_{config.table_name}_snapshot.json"
        self.change_tracker = ChangeTracker(config.business_keys)
        self.current_snapshot = {}
        self.previous_snapshot = {}
    
    def run(self) -> bool:
        """
        Execute complete CDC process
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting CDC process for table: {self.config.table_name}")
            
            # Step 1: Load current data from CSV
            logger.info(f"Loading CSV file: {self.config.source_file_path}")
            current_data = self._load_csv_data()
            if current_data is None:
                logger.error("Failed to load CSV data")
                return False
            
            # Step 2: Load previous snapshot
            logger.info("Loading previous snapshot")
            previous_data = self._load_snapshot()
            
            # Step 3: Detect changes
            logger.info("Detecting changes...")
            self.change_tracker.detect_changes(previous_data, current_data)
            self.change_tracker.print_summary()
            
            # Step 4: Apply changes to database
            logger.info("Applying changes to Oracle database...")
            if not self.db_connector.connect():
                logger.error("Failed to connect to database")
                return False
            
            success = self._apply_changes_to_db()
            
            # Step 5: Save current snapshot
            if success:
                logger.info("Saving current snapshot")
                self._save_snapshot(current_data)
            
            self.db_connector.disconnect()
            
            logger.info("CDC process completed successfully")
            return success
            
        except Exception as e:
            logger.error(f"Error in CDC process: {str(e)}")
            return False
    
    def _load_csv_data(self) -> Optional[Dict[int, Dict[str, Any]]]:
        """
        Load data from CSV file
        
        Returns:
            Dictionary of rows indexed by row number, or None if failed
        """
        try:
            df = pd.read_csv(self.config.source_file_path)
            
            # Validate columns exist
            csv_columns = set(df.columns)
            required_columns = set(self.config.get_column_names())
            
            missing_columns = required_columns - csv_columns
            if missing_columns:
                logger.error(f"Missing columns in CSV: {missing_columns}")
                return None
            
            # Convert to dictionary format
            data_dict = {}
            for idx, row in df.iterrows():
                row_data = {}
                for col_name in self.config.get_column_names():
                    row_data[col_name] = str(row[col_name]).strip()
                data_dict[idx] = row_data
            
            logger.info(f"Loaded {len(data_dict)} rows from CSV")
            self.current_snapshot = data_dict
            return data_dict
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            return None
    
    def _load_snapshot(self) -> Dict[int, Dict[str, Any]]:
        """
        Load previous snapshot from file
        
        Returns:
            Dictionary of rows, or empty dict if snapshot doesn't exist
        """
        try:
            snapshot_path = Path(self.snapshot_file)
            if snapshot_path.exists():
                with open(snapshot_path, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    self.previous_snapshot = {int(k): v for k, v in data.items()}
                    logger.info(f"Loaded snapshot with {len(self.previous_snapshot)} rows")
                    return self.previous_snapshot
            else:
                logger.info("No previous snapshot found (first run)")
                return {}
        except Exception as e:
            logger.warning(f"Error loading snapshot: {str(e)}")
            return {}
    
    def _save_snapshot(self, data: Dict[int, Dict[str, Any]]) -> bool:
        """
        Save current snapshot to file
        
        Args:
            data: Current data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.snapshot_file, 'w') as f:
                # Convert integer keys to strings for JSON serialization
                json_data = {str(k): v for k, v in data.items()}
                json.dump(json_data, f, indent=2)
            logger.info(f"Snapshot saved to {self.snapshot_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving snapshot: {str(e)}")
            return False
    
    def _apply_changes_to_db(self) -> bool:
        """
        Apply detected changes to Oracle database
        
        Returns:
            True if all changes applied successfully, False otherwise
        """
        try:
            changes = self.change_tracker.get_changes()
            total_changes = len(changes)
            
            if total_changes == 0:
                logger.info("No changes to apply")
                return True
            
            successful = 0
            
            for idx, change in enumerate(changes, 1):
                logger.info(f"Processing change {idx}/{total_changes}: {change.change_type.value}")
                
                if change.change_type == ChangeType.INSERT:
                    success = self._process_insert(change)
                elif change.change_type == ChangeType.UPDATE:
                    success = self._process_update(change)
                elif change.change_type == ChangeType.DELETE:
                    success = self._process_delete(change)
                else:
                    success = False
                
                if success:
                    successful += 1
                    self.db_connector.commit()
                else:
                    self.db_connector.rollback()
            
            logger.info(f"Successfully applied {successful}/{total_changes} changes")
            return successful == total_changes
            
        except Exception as e:
            logger.error(f"Error applying changes: {str(e)}")
            return False
    
    def _process_insert(self, change: ChangeRecord) -> bool:
        """Process an INSERT change"""
        try:
            logger.debug(f"INSERT: {change.business_keys}")
            return self.db_connector.insert_new_record(
                self.config.oracle_table_name,
                change.new_values,
                self.config.start_date_column,
                self.config.end_date_column,
                self.config.row_status_column
            )
        except Exception as e:
            logger.error(f"Error processing INSERT: {str(e)}")
            return False
    
    def _process_update(self, change: ChangeRecord) -> bool:
        """Process an UPDATE change"""
        try:
            logger.debug(f"UPDATE: {change.business_keys}, Changed columns: {change.changed_columns}")
            return self.db_connector.expire_and_insert_update(
                self.config.oracle_table_name,
                change.old_values,
                change.new_values,
                self.config.business_keys,
                change.changed_columns,
                self.config.end_date_column,
                self.config.start_date_column,
                self.config.row_status_column
            )
        except Exception as e:
            logger.error(f"Error processing UPDATE: {str(e)}")
            return False
    
    def _process_delete(self, change: ChangeRecord) -> bool:
        """Process a DELETE change"""
        try:
            logger.debug(f"DELETE: {change.business_keys}")
            return self.db_connector.delete_record(
                self.config.oracle_table_name,
                self.config.business_keys,
                change.business_keys,
                self.config.end_date_column,
                self.config.row_status_column
            )
        except Exception as e:
            logger.error(f"Error processing DELETE: {str(e)}")
            return False
    
    def get_change_summary(self) -> Dict[str, int]:
        """
        Get summary of changes
        
        Returns:
            Dictionary with change counts
        """
        return {
            'total': len(self.change_tracker.get_changes()),
            'inserts': self.change_tracker.get_insert_count(),
            'updates': self.change_tracker.get_update_count(),
            'deletes': self.change_tracker.get_delete_count()
        }

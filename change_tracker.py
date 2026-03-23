"""
Change Tracking Module
Detects and tracks changes (Insert, Update, Delete) in data
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ChangeRecord:
    """Represents a single change"""
    change_type: ChangeType
    business_keys: Dict[str, any]
    old_values: Optional[Dict[str, any]]
    new_values: Optional[Dict[str, any]]
    changed_columns: List[str]
    timestamp: datetime


class ChangeTracker:
    """Detects data changes and tracks them"""
    
    def __init__(self, business_keys: List[str]):
        """
        Initialize change tracker
        
        Args:
            business_keys: List of column names that form the business key
        """
        self.business_keys = business_keys
        self.changes: List[ChangeRecord] = []
    
    def detect_changes(self, old_data: Dict[str, Dict[str, any]],
                      new_data: Dict[str, Dict[str, any]]) -> List[ChangeRecord]:
        """
        Detect all changes between old and new data
        
        Args:
            old_data: Previous data keyed by business key tuple
            new_data: Current data keyed by business key tuple
            
        Returns:
            List of ChangeRecord objects
        """
        self.changes = []
        
        # Convert data to keyable format
        old_keys = set(self._get_row_key(row, old_data) for row in old_data.values())
        new_keys = set(self._get_row_key(row, new_data) for row in new_data.values())
        
        # Detect inserts
        insert_keys = new_keys - old_keys
        for key in insert_keys:
            new_row = self._get_row_by_key(key, new_data)
            if new_row:
                self.changes.append(ChangeRecord(
                    change_type=ChangeType.INSERT,
                    business_keys=self._extract_business_keys(new_row),
                    old_values=None,
                    new_values=new_row,
                    changed_columns=list(new_row.keys()),
                    timestamp=datetime.now()
                ))
                logger.debug(f"Detected INSERT for {key}")
        
        # Detect deletes
        delete_keys = old_keys - new_keys
        for key in delete_keys:
            old_row = self._get_row_by_key(key, old_data)
            if old_row:
                self.changes.append(ChangeRecord(
                    change_type=ChangeType.DELETE,
                    business_keys=self._extract_business_keys(old_row),
                    old_values=old_row,
                    new_values=None,
                    changed_columns=[],
                    timestamp=datetime.now()
                ))
                logger.debug(f"Detected DELETE for {key}")
        
        # Detect updates
        update_keys = old_keys & new_keys
        for key in update_keys:
            old_row = self._get_row_by_key(key, old_data)
            new_row = self._get_row_by_key(key, new_data)
            
            if old_row and new_row:
                changed_cols = self._find_changed_columns(old_row, new_row)
                if changed_cols:
                    self.changes.append(ChangeRecord(
                        change_type=ChangeType.UPDATE,
                        business_keys=self._extract_business_keys(new_row),
                        old_values=old_row,
                        new_values=new_row,
                        changed_columns=changed_cols,
                        timestamp=datetime.now()
                    ))
                    logger.debug(f"Detected UPDATE for {key}, columns: {changed_cols}")
        
        return self.changes
    
    def _get_row_key(self, row: Dict[str, any], data_dict: Dict) -> Tuple:
        """Get business key tuple for a row"""
        return tuple(row.get(bk) for bk in self.business_keys)
    
    def _extract_business_keys(self, row: Dict[str, any]) -> Dict[str, any]:
        """Extract business key columns from a row"""
        return {bk: row.get(bk) for bk in self.business_keys}
    
    def _get_row_by_key(self, key: Tuple, data_dict: Dict) -> Optional[Dict]:
        """Find a row by its business key"""
        for row in data_dict.values():
            if self._get_row_key(row, data_dict) == key:
                return row
        return None
    
    def _find_changed_columns(self, old_row: Dict[str, any],
                             new_row: Dict[str, any]) -> List[str]:
        """
        Find which columns have changed
        
        Args:
            old_row: Old row data
            new_row: New row data
            
        Returns:
            List of column names that changed
        """
        changed = []
        all_cols = set(old_row.keys()) | set(new_row.keys())
        
        for col in all_cols:
            old_val = old_row.get(col)
            new_val = new_row.get(col)
            
            # Handle None/empty comparisons
            if str(old_val).strip() != str(new_val).strip():
                changed.append(col)
        
        return changed
    
    def get_changes(self) -> List[ChangeRecord]:
        """Get all detected changes"""
        return self.changes
    
    def get_changes_by_type(self, change_type: ChangeType) -> List[ChangeRecord]:
        """Get changes filtered by type"""
        return [c for c in self.changes if c.change_type == change_type]
    
    def get_insert_count(self) -> int:
        """Get count of INSERT changes"""
        return len(self.get_changes_by_type(ChangeType.INSERT))
    
    def get_update_count(self) -> int:
        """Get count of UPDATE changes"""
        return len(self.get_changes_by_type(ChangeType.UPDATE))
    
    def get_delete_count(self) -> int:
        """Get count of DELETE changes"""
        return len(self.get_changes_by_type(ChangeType.DELETE))
    
    def print_summary(self):
        """Print a summary of detected changes"""
        total = len(self.changes)
        inserts = self.get_insert_count()
        updates = self.get_update_count()
        deletes = self.get_delete_count()
        
        logger.info("=" * 60)
        logger.info("CDC SUMMARY REPORT")
        logger.info("=" * 60)
        logger.info(f"Total Changes: {total}")
        logger.info(f"  - Inserts: {inserts}")
        logger.info(f"  - Updates: {updates}")
        logger.info(f"  - Deletes: {deletes}")
        logger.info("=" * 60)

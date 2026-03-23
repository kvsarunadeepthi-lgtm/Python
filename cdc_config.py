"""
CDC Configuration Module
Handles loading and validating table configuration from JSON
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ColumnConfig:
    """Configuration for a single column"""
    name: str
    data_type: str
    is_primary_key: bool = False
    is_business_key: bool = False
    nullable: bool = True


@dataclass
class TableConfig:
    """Configuration for a CDC table"""
    table_name: str
    source_file_path: str
    oracle_table_name: str
    columns: List[ColumnConfig]
    business_keys: List[str]
    timestamp_column: str = "CDC_TIMESTAMP"
    end_date_column: str = "END_DATE"
    start_date_column: str = "START_DATE"
    row_status_column: str = "RECORD_STATUS"
    
    def get_primary_keys(self) -> List[str]:
        """Get list of primary key column names"""
        return [col.name for col in self.columns if col.is_primary_key]
    
    def get_column_names(self) -> List[str]:
        """Get all column names"""
        return [col.name for col in self.columns]
    
    def get_column_by_name(self, name: str) -> ColumnConfig:
        """Get column configuration by name"""
        for col in self.columns:
            if col.name == name:
                return col
        raise ValueError(f"Column {name} not found in configuration")


class CDCConfigLoader:
    """Loads CDC configuration from JSON file"""
    
    @staticmethod
    def load_config(config_path: str) -> TableConfig:
        """
        Load configuration from JSON file
        
        Args:
            config_path: Path to JSON configuration file
            
        Returns:
            TableConfig object populated from JSON
        """
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Parse columns
        columns = []
        for col_data in config_data.get('columns', []):
            column = ColumnConfig(
                name=col_data['name'],
                data_type=col_data.get('data_type', 'VARCHAR2'),
                is_primary_key=col_data.get('is_primary_key', False),
                is_business_key=col_data.get('is_business_key', False),
                nullable=col_data.get('nullable', True)
            )
            columns.append(column)
        
        # Create TableConfig
        table_config = TableConfig(
            table_name=config_data['table_name'],
            source_file_path=config_data['source_file_path'],
            oracle_table_name=config_data['oracle_table_name'],
            columns=columns,
            business_keys=config_data.get('business_keys', []),
            timestamp_column=config_data.get('timestamp_column', 'CDC_TIMESTAMP'),
            end_date_column=config_data.get('end_date_column', 'END_DATE'),
            start_date_column=config_data.get('start_date_column', 'START_DATE'),
            row_status_column=config_data.get('row_status_column', 'RECORD_STATUS')
        )
        
        return table_config
    
    @staticmethod
    def validate_config(config: TableConfig) -> bool:
        """
        Validate configuration
        
        Args:
            config: TableConfig to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not config.table_name:
            raise ValueError("table_name is required")
        if not config.source_file_path:
            raise ValueError("source_file_path is required")
        if not config.oracle_table_name:
            raise ValueError("oracle_table_name is required")
        if not config.columns:
            raise ValueError("At least one column must be defined")
        if not config.business_keys:
            raise ValueError("business_keys must be defined for CDC tracking")
        
        # Verify all business keys exist in columns
        column_names = config.get_column_names()
        for bk in config.business_keys:
            if bk not in column_names:
                raise ValueError(f"Business key '{bk}' not found in columns")
        
        return True

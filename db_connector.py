"""
Oracle Database Connector Module
Handles connections to Oracle database and CDC data writes
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OracleConnector:
    """Manages Oracle database connections and CDC operations"""
    
    def __init__(self, connection_string: str, username: str, password: str):
        """
        Initialize Oracle connector
        
        Args:
            connection_string: Oracle connection string (e.g., 'localhost:1521/ORCL')
            username: Database username
            password: Database password
        """
        self.connection_string = connection_string
        self.username = username
        self.password = password
        self.connection = None
        self.cursor = None
        
        # Try to import cx_Oracle
        try:
            import cx_Oracle
            self.cx_Oracle = cx_Oracle
        except ImportError:
            logger.warning("cx_Oracle not installed. Install with: pip install cx-Oracle")
            self.cx_Oracle = None
    
    def connect(self) -> bool:
        """
        Establish connection to Oracle database
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.cx_Oracle is None:
                logger.error("cx_Oracle module not available")
                return False
            
            self.connection = self.cx_Oracle.connect(
                self.username,
                self.password,
                self.connection_string
            )
            self.cursor = self.connection.cursor()
            logger.info(f"Connected to Oracle database: {self.connection_string}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Oracle: {str(e)}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
                logger.info("Disconnected from Oracle database")
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
    
    def create_cdc_table(self, table_name: str, columns: List[Dict[str, Any]],
                        business_keys: List[str], start_date_col: str,
                        end_date_col: str, status_col: str) -> bool:
        """
        Create CDC tracking table in Oracle
        
        Args:
            table_name: Name of table to create
            columns: List of column definitions [{'name': 'col1', 'type': 'VARCHAR2(100)'}]
            business_keys: List of business key column names
            start_date_col: Name of start date column
            end_date_col: Name of end date column
            status_col: Name of status column
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build CREATE TABLE statement
            col_defs = [f'"{col["name"]}" {col["type"]}' for col in columns]
            col_defs.append(f'"{start_date_col}" DATE DEFAULT TRUNC(SYSDATE)')
            col_defs.append(f'"{end_date_col}" DATE DEFAULT TO_DATE(\'31-DEC-9999\', \'DD-MON-YYYY\')')
            col_defs.append(f'"{status_col}" VARCHAR2(10) DEFAULT \'ACTIVE\'')
            col_defs.append('"CDC_TIMESTAMP" TIMESTAMP DEFAULT SYSTIMESTAMP')
            
            create_sql = f"""
            CREATE TABLE {table_name} (
                {','.join(col_defs)}
            )
            """
            
            self.cursor.execute(create_sql)
            self.connection.commit()
            logger.info(f"Created CDC table: {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            return False
    
    def insert_new_record(self, table_name: str, data: Dict[str, Any],
                         start_date_col: str, end_date_col: str, status_col: str) -> bool:
        """
        Insert a new record (INSERT operation)
        
        Args:
            table_name: Target table name
            data: Dictionary of column names and values
            start_date_col: Start date column name
            end_date_col: End date column name
            status_col: Status column name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add CDC columns
            data_copy = data.copy()
            data_copy[start_date_col] = 'TRUNC(SYSDATE)'
            data_copy[end_date_col] = "TO_DATE('31-DEC-9999', 'DD-MON-YYYY')"
            data_copy[status_col] = 'ACTIVE'
            
            columns = ', '.join([f'"{col}"' for col in data_copy.keys()])
            values_list = []
            placeholders = []
            
            for key, value in data_copy.items():
                if value in ['TRUNC(SYSDATE)', "TO_DATE('31-DEC-9999', 'DD-MON-YYYY')"]:
                    placeholders.append(value)
                else:
                    placeholders.append(':' + key)
                    values_list.append(value)
            
            values_str = ', '.join(placeholders)
            insert_sql = f'INSERT INTO {table_name} ({columns}) VALUES ({values_str})'
            
            self.cursor.execute(insert_sql, {f'{key}': data[key] for key in data})
            logger.debug(f"Inserted new record into {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert record: {str(e)}")
            return False
    
    def expire_and_insert_update(self, table_name: str, old_data: Dict[str, Any],
                                  new_data: Dict[str, Any], business_keys: List[str],
                                  changed_columns: List[str], end_date_col: str,
                                  start_date_col: str, status_col: str) -> bool:
        """
        Handle UPDATE: Expire old record and insert new one (SCD Type 2)
        
        Args:
            table_name: Target table name
            old_data: Previous values
            new_data: New values
            business_keys: Business key columns
            changed_columns: List of columns that changed
            end_date_col: End date column name
            start_date_col: Start date column name
            status_col: Status column name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Expire old record
            where_clause = ' AND '.join([f'"{bk}" = :{bk}' for bk in business_keys])
            where_params = {bk: old_data[bk] for bk in business_keys}
            
            expire_sql = f"""
            UPDATE {table_name} 
            SET "{end_date_col}" = TRUNC(SYSDATE) - 1, 
                "{status_col}" = 'EXPIRED'
            WHERE {where_clause} AND "{end_date_col}" = TO_DATE('31-DEC-9999', 'DD-MON-YYYY')
            """
            
            self.cursor.execute(expire_sql, where_params)
            
            # Step 2: Insert new record
            new_data_copy = new_data.copy()
            new_data_copy[start_date_col] = 'TRUNC(SYSDATE)'
            new_data_copy[end_date_col] = "TO_DATE('31-DEC-9999', 'DD-MON-YYYY')"
            new_data_copy[status_col] = 'ACTIVE'
            new_data_copy['CHANGED_COLUMNS'] = ', '.join(changed_columns)
            
            columns = ', '.join([f'"{col}"' for col in new_data_copy.keys() if col != 'CHANGED_COLUMNS'])
            columns += ', "CHANGED_COLUMNS"'
            placeholders = ', '.join([':' + col for col in new_data_copy.keys()])
            
            insert_sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'
            self.cursor.execute(insert_sql, new_data_copy)
            
            logger.debug(f"Updated record in {table_name} (columns changed: {changed_columns})")
            return True
        except Exception as e:
            logger.error(f"Failed to update record: {str(e)}")
            return False
    
    def delete_record(self, table_name: str, business_keys: List[str],
                     business_key_values: Dict[str, Any], end_date_col: str,
                     status_col: str) -> bool:
        """
        Handle DELETE: Expire the record
        
        Args:
            table_name: Target table name
            business_keys: Business key column names
            business_key_values: Business key values
            end_date_col: End date column name
            status_col: Status column name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            where_clause = ' AND '.join([f'"{bk}" = :{bk}' for bk in business_keys])
            
            delete_sql = f"""
            UPDATE {table_name}
            SET "{end_date_col}" = TRUNC(SYSDATE) - 1,
                "{status_col}" = 'DELETED'
            WHERE {where_clause} AND "{end_date_col}" = TO_DATE('31-DEC-9999', 'DD-MON-YYYY')
            """
            
            self.cursor.execute(delete_sql, business_key_values)
            logger.debug(f"Deleted (expired) record in {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete record: {str(e)}")
            return False
    
    def commit(self):
        """Commit transaction"""
        try:
            if self.connection:
                self.connection.commit()
                logger.debug("Transaction committed")
        except Exception as e:
            logger.error(f"Error committing transaction: {str(e)}")
    
    def rollback(self):
        """Rollback transaction"""
        try:
            if self.connection:
                self.connection.rollback()
                logger.warning("Transaction rolled back")
        except Exception as e:
            logger.error(f"Error rolling back transaction: {str(e)}")
    
    def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """
        Execute a SELECT query
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            columns = [desc[0] for desc in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return []

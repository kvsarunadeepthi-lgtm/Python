import json
import pandas as pd
import sqlite3
import os
from datetime import datetime
import logging
from typing import Dict, List, Any

# Try to import Oracle client
try:
    import oracledb
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    logger_placeholder = logging.getLogger(__name__)
    logger_placeholder.warning("oracledb not installed. Oracle support will be limited.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metadata_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MetadataBasedDataLoader:
    """
    Generic data loader that uses JSON metadata to load CSV files.
    The JSON metadata defines column mappings, transformations, and target structure.
    """
    
    def __init__(self, metadata_file: str, csv_file: str = None, 
                 oracle_config: Dict[str, str] = None):
        """
        Initialize the loader
        
        Args:
            metadata_file (str): Path to JSON metadata file
            csv_file (str): Path to CSV file (can be specified in init or loaded from metadata)
            oracle_config (Dict): Oracle connection config with keys:
                - username: Oracle username
                - password: Oracle password
                - dsn: Data Source Name (host:port/service_name)
                Example: {"username": "hr", "password": "pass", "dsn": "localhost:1521/ORCL"}
        """
        self.metadata_file = metadata_file
        self.csv_file = csv_file
        self.metadata = None
        self.source_data = None
        self.transformed_data = None
        self.column_mappings = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.oracle_config = oracle_config or {}
    
    def load_metadata(self) -> bool:
        """Load JSON metadata file"""
        try:
            logger.info(f"Loading metadata from: {self.metadata_file}")
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            logger.info(f"Successfully loaded metadata")
            return True
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            return False
    
    def extract_column_mappings(self) -> Dict[str, Dict]:
        """
        Extract column mappings from metadata.
        Creates mapping from source columns to target columns with transformation rules.
        
        Returns:
            Dict: Column mapping dictionary
        """
        try:
            logger.info("Extracting column mappings from metadata")
            
            self.column_mappings = {}
            
            # Iterate through all sheets in metadata
            for sheet_name, records in self.metadata.items():
                logger.info(f"Processing sheet: {sheet_name}")
                
                for record in records:
                    source_col = record.get('source column name', '')
                    target_col = record.get('target column name', '')
                    source_table = record.get('source table name', '')
                    target_table = record.get('target table name', '')
                    datatype = record.get('Datatype', '')
                    primary_key = record.get('Primary key', 'N')
                    is_null = record.get('is Null', 'Y')
                    transformation = record.get('transformation logic', 'direct move')
                    column_order = record.get('column order', 999)
                    
                    if source_col and target_col:
                        self.column_mappings[source_col.lower()] = {
                            'source_column': source_col,
                            'target_column': target_col,
                            'source_table': source_table,
                            'target_table': target_table,
                            'datatype': datatype,
                            'primary_key': primary_key,
                            'is_null': is_null,
                            'transformation': transformation,
                            'column_order': column_order
                        }
                        logger.info(f"  Mapped: {source_col} -> {target_col}")
            
            logger.info(f"Total column mappings extracted: {len(self.column_mappings)}")
            return self.column_mappings
        
        except Exception as e:
            logger.error(f"Error extracting column mappings: {str(e)}")
            return {}
    
    def load_csv(self, csv_file: str = None) -> bool:
        """
        Load CSV file based on metadata
        
        Args:
            csv_file (str): Path to CSV file
            
        Returns:
            bool: Success status
        """
        try:
            target_csv = csv_file or self.csv_file
            
            if not target_csv:
                logger.error("CSV file path not specified")
                return False
            
            if not os.path.exists(target_csv):
                logger.error(f"CSV file not found: {target_csv}")
                return False
            
            logger.info(f"Loading CSV file: {target_csv}")
            self.source_data = pd.read_csv(target_csv)
            logger.info(f"Successfully loaded {len(self.source_data)} rows and {len(self.source_data.columns)} columns")
            logger.info(f"Columns: {list(self.source_data.columns)}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            return False
    
    def transform_data(self) -> bool:
        """
        Transform data using metadata mappings
        
        Returns:
            bool: Success status
        """
        try:
            logger.info("Starting data transformation")
            
            if self.source_data is None:
                logger.error("No source data loaded")
                return False
            
            if not self.column_mappings:
                logger.error("No column mappings available")
                return False
            
            # Create new dataframe with transformed columns
            transformed_df = pd.DataFrame()
            
            # Get sorted column order from metadata
            sorted_mappings = sorted(
                self.column_mappings.items(),
                key=lambda x: x[1]['column_order']
            )
            
            for source_col_lower, mapping in sorted_mappings:
                source_col = mapping['source_column']
                target_col = mapping['target_column']
                
                # Find the source column (case-insensitive)
                matched_col = None
                for col in self.source_data.columns:
                    if col.lower() == source_col_lower:
                        matched_col = col
                        break
                
                if matched_col:
                    transformation = mapping.get('transformation', 'direct move')
                    
                    # Apply transformation logic
                    if transformation == 'direct move':
                        transformed_df[target_col] = self.source_data[matched_col]
                    elif transformation == 'uppercase':
                        transformed_df[target_col] = self.source_data[matched_col].str.upper()
                    elif transformation == 'lowercase':
                        transformed_df[target_col] = self.source_data[matched_col].str.lower()
                    elif transformation == 'trim':
                        transformed_df[target_col] = self.source_data[matched_col].str.strip()
                    else:
                        # Default to direct move for unknown transformations
                        transformed_df[target_col] = self.source_data[matched_col]
                    
                    logger.info(f"Transformed: {source_col} -> {target_col} ({transformation})")
                else:
                    # Skip columns that don't exist in source data
                    logger.warning(f"Source column not found: {source_col} (skipping)")
            
            self.transformed_data = transformed_df
            logger.info(f"Transformation complete: {len(self.transformed_data)} rows and {len(self.transformed_data.columns)} columns")
            logger.info(f"Transformed columns: {list(self.transformed_data.columns)}")
            return True
        
        except Exception as e:
            logger.error(f"Error during transformation: {str(e)}")
            return False
    
    def load_to_csv(self, output_dir: str = 'output') -> str:
        """Load to CSV file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"transformed_emp_{self.timestamp}.csv")
            self.transformed_data.to_csv(output_file, index=False, encoding='utf-8')
            logger.info(f"Data loaded to CSV: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return None
    
    def load_to_json(self, output_dir: str = 'output') -> str:
        """Load to JSON file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"transformed_emp_{self.timestamp}.json")
            self.transformed_data.to_json(output_file, orient='records', indent=2, force_ascii=False)
            logger.info(f"Data loaded to JSON: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")
            return None
    
    def load_to_sqlite(self, db_file: str = 'output/data.db', table_name: str = 'EMP') -> str:
        """Load to SQLite database"""
        try:
            os.makedirs(os.path.dirname(db_file) or '.', exist_ok=True)
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Drop table if exists
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Create table with metadata constraints
            create_table_sql = self._generate_create_table_sql(table_name, db_type='sqlite')
            logger.info(f"Creating table with SQL:\n{create_table_sql}")
            cursor.execute(create_table_sql)
            
            # Insert data - pandas handles NULL values automatically
            self.transformed_data.to_sql(table_name, conn, if_exists='append', index=False)
            conn.commit()
            conn.close()
            
            logger.info(f"Data loaded to SQLite: {db_file}, Table: {table_name}")
            return db_file
        
        except Exception as e:
            logger.error(f"Error saving to SQLite: {str(e)}")
            return None
    
    def load_to_oracle(self, table_name: str = 'EMP', drop_table: bool = True) -> bool:
        """
        Load data to Oracle database
        
        Args:
            table_name (str): Target table name in Oracle
            drop_table (bool): Whether to drop and recreate the table
            
        Returns:
            bool: Success status
        """
        try:
            if not ORACLE_AVAILABLE:
                logger.error("oracledb package not installed. Install with: pip install oracledb")
                return False
            
            if not self.oracle_config:
                logger.error("Oracle configuration not provided")
                logger.info("Provide oracle_config with: {'username': '...', 'password': '...', 'dsn': '...'}")
                return False
            
            logger.info(f"Connecting to Oracle database...")
            
            # Create connection
            conn = oracledb.connect(
                user=self.oracle_config.get('username'),
                password=self.oracle_config.get('password'),
                dsn=self.oracle_config.get('dsn')
            )
            cursor = conn.cursor()
            
            # Drop table if exists
            if drop_table:
                try:
                    cursor.execute(f"DROP TABLE {table_name}")
                    conn.commit()
                    logger.info(f"Dropped existing table: {table_name}")
                except:
                    pass  # Table might not exist
            
            # Create table with metadata constraints
            create_table_sql = self._generate_create_table_sql(table_name, db_type='oracle')
            logger.info(f"Creating table with SQL:\n{create_table_sql}")
            cursor.execute(create_table_sql)
            conn.commit()
            
            # Insert data
            self._insert_data_to_oracle(cursor, table_name)
            conn.commit()
            
            logger.info(f"Data loaded to Oracle: Table={table_name}, Rows={len(self.transformed_data)}")
            cursor.close()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving to Oracle: {str(e)}")
            return False
    
    def _insert_data_to_oracle(self, cursor, table_name: str) -> None:
        """Insert data into Oracle table"""
        try:
            columns = ','.join(self.transformed_data.columns)
            placeholders = ','.join(['?' for _ in self.transformed_data.columns])
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            # Convert dataframe rows to tuples
            data_tuples = [tuple(row) for row in self.transformed_data.values]
            
            cursor.executemany(insert_sql, data_tuples)
            logger.info(f"Inserted {len(data_tuples)} rows into {table_name}")
        
        except Exception as e:
            logger.error(f"Error inserting data to Oracle: {str(e)}")
            raise
    
    def _generate_create_table_sql(self, table_name: str, db_type: str = 'sqlite') -> str:
        """
        Generate CREATE TABLE SQL from metadata
        
        Args:
            table_name (str): Name of the table
            db_type (str): Database type ('sqlite' or 'oracle')
        """
        sql_lines = [f"CREATE TABLE {table_name} ("]
        
        sorted_mappings = sorted(
            self.column_mappings.items(),
            key=lambda x: x[1]['column_order']
        )
        
        primary_key_found = False  # Only use first primary key
        column_count = 0
        
        for idx, (_, mapping) in enumerate(sorted_mappings):
            target_col = mapping['target_column']
            
            # Only include columns that exist in transformed data
            if target_col not in self.transformed_data.columns:
                logger.debug(f"Skipping column {target_col} - not in transformed data")
                continue
            
            datatype = mapping.get('Datatype.1', 'TEXT')  # Use target datatype
            is_null = mapping.get('is_null', 'Y')
            primary_key = mapping.get('primary_key', 'N')
            
            # Convert datatype based on database type
            sql_type = self._convert_datatype(datatype, db_type)
            
            constraint = ""
            # Only use first primary key
            if primary_key.upper() == 'Y' and not primary_key_found:
                constraint += " PRIMARY KEY"
                primary_key_found = True
            if is_null.upper() == 'N':
                constraint += " NOT NULL"
            
            sql_lines.append(f"  {target_col} {sql_type}{constraint}")
            column_count += 1
            
            if column_count > 0:
                sql_lines[-1] += ","
        
        # Remove trailing comma from last column
        if len(sql_lines) > 1:
            sql_lines[-1] = sql_lines[-1].rstrip(',')
        
        sql_lines.append(")")
        return "\n".join(sql_lines)
    
    def _convert_datatype(self, datatype: str, db_type: str = 'sqlite') -> str:
        """
        Convert datatype from metadata to target database type
        
        Args:
            datatype (str): Original datatype from metadata
            db_type (str): Target database type ('sqlite' or 'oracle')
            
        Returns:
            str: Converted datatype
        """
        datatype_lower = datatype.lower()
        
        if db_type == 'oracle':
            # Oracle datatype mappings
            if 'integer' in datatype_lower:
                return 'NUMBER(10)'
            elif 'varchar' in datatype_lower:
                # Extract size if available
                if '(' in datatype and ')' in datatype:
                    size = datatype.split('(')[1].split(')')[0]
                    return f'VARCHAR2({size})'
                return 'VARCHAR2(255)'
            elif 'date' in datatype_lower:
                return 'DATE'
            elif 'timestamp' in datatype_lower:
                return 'TIMESTAMP'
            elif 'decimal' in datatype_lower or 'numeric' in datatype_lower:
                return 'NUMBER(10,2)'
            else:
                return 'VARCHAR2(255)'
        else:
            # SQLite datatype mappings
            if 'integer' in datatype_lower:
                return 'INTEGER'
            elif 'varchar' in datatype_lower:
                return 'TEXT'
            elif 'date' in datatype_lower:
                return 'TEXT'
            elif 'timestamp' in datatype_lower:
                return 'TEXT'
            else:
                return 'TEXT'
    
    def load_to_excel(self, output_dir: str = 'output') -> str:
        """Load to Excel file"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"transformed_emp_{self.timestamp}.xlsx")
            self.transformed_data.to_excel(output_file, sheet_name='Data', index=False)
            logger.info(f"Data loaded to Excel: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving to Excel: {str(e)}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transformation statistics"""
        return {
            'source_rows': len(self.source_data) if self.source_data is not None else 0,
            'source_columns': len(self.source_data.columns) if self.source_data is not None else 0,
            'transformed_rows': len(self.transformed_data) if self.transformed_data is not None else 0,
            'transformed_columns': len(self.transformed_data.columns) if self.transformed_data is not None else 0,
            'column_mappings': len(self.column_mappings),
            'timestamp': self.timestamp
        }
    
    def run_pipeline(self, csv_file: str = None, output_formats: List[str] = None) -> bool:
        """
        Run the complete pipeline: Load Metadata -> Load CSV -> Transform -> Load to Outputs
        
        Args:
            csv_file (str): Path to CSV file
            output_formats (List[str]): Output formats ['csv', 'json', 'sqlite', 'excel']
            
        Returns:
            bool: Success status
        """
        try:
            if output_formats is None:
                output_formats = ['csv', 'json', 'sqlite', 'excel']
            
            logger.info("=" * 60)
            logger.info("Starting Metadata-Based Data Loading Pipeline")
            logger.info("=" * 60)
            
            # Step 1: Load metadata
            if not self.load_metadata():
                logger.error("Failed to load metadata")
                return False
            
            # Step 2: Extract column mappings
            self.extract_column_mappings()
            
            # Step 3: Load CSV
            target_csv = csv_file or self.csv_file
            if not self.load_csv(target_csv):
                logger.error("Failed to load CSV")
                return False
            
            # Step 4: Transform data
            if not self.transform_data():
                logger.error("Failed to transform data")
                return False
            
            # Step 5: Load to outputs
            logger.info("Loading to output formats...")
            if 'csv' in output_formats:
                self.load_to_csv()
            if 'json' in output_formats:
                self.load_to_json()
            if 'sqlite' in output_formats:
                self.load_to_sqlite()
            if 'excel' in output_formats:
                self.load_to_excel()
            
            # Display statistics
            stats = self.get_statistics()
            logger.info("\n" + "=" * 60)
            logger.info("Transformation Statistics")
            logger.info("=" * 60)
            logger.info(f"Source Rows: {stats['source_rows']}")
            logger.info(f"Source Columns: {stats['source_columns']}")
            logger.info(f"Transformed Rows: {stats['transformed_rows']}")
            logger.info(f"Transformed Columns: {stats['transformed_columns']}")
            logger.info(f"Column Mappings: {stats['column_mappings']}")
            
            logger.info("\n" + "=" * 60)
            logger.info("Pipeline Completed Successfully!")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            return False


if __name__ == "__main__":
    # Initialize loader
    loader = MetadataBasedDataLoader(
        metadata_file='sttm.json',
        csv_file='emp.csv'
    )
    
    # Run pipeline
    success = loader.run_pipeline(
        csv_file='emp.csv',
        output_formats=['csv', 'json', 'sqlite', 'excel']
    )
    
    if success:
        print("\n✓ Data loading pipeline completed successfully!")
    else:
        print("\n✗ Data loading pipeline failed!")

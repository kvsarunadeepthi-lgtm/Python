import json
import pandas as pd
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """ETL Pipeline for processing JSON data"""
    
    def __init__(self, input_json_file):
        """
        Initialize ETL Pipeline
        
        Args:
            input_json_file (str): Path to the input JSON file
        """
        self.input_file = input_json_file
        self.raw_data = None
        self.transformed_data = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def extract(self):
        """Extract: Read data from JSON file"""
        try:
            logger.info(f"Extracting data from {self.input_file}")
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)
            logger.info(f"Successfully extracted {len(self.raw_data)} sheets")
            return self.raw_data
        except Exception as e:
            logger.error(f"Error during extraction: {str(e)}")
            raise
    
    def transform(self):
        """Transform: Clean and enrich data"""
        try:
            logger.info("Transforming data...")
            
            if not self.raw_data:
                raise ValueError("No data to transform. Run extract() first.")
            
            for sheet_name, records in self.raw_data.items():
                logger.info(f"Processing sheet: {sheet_name} ({len(records)} records)")
                
                # Convert to DataFrame for easier manipulation
                df = pd.DataFrame(records)
                
                # Data cleaning transformations
                # Remove duplicates
                df = df.drop_duplicates()
                logger.info(f"  - Removed duplicates: {len(records) - len(df)} rows removed")
                
                # Handle missing values
                missing_count = df.isnull().sum().sum()
                df = df.fillna('N/A')
                logger.info(f"  - Handled {missing_count} missing values")
                
                # Remove leading/trailing whitespace from string columns
                for col in df.select_dtypes(include=['object']).columns:
                    df[col] = df[col].str.strip()
                
                # Add metadata
                df['_load_timestamp'] = datetime.now().isoformat()
                df['_source_sheet'] = sheet_name
                
                self.transformed_data[sheet_name] = df
                logger.info(f"  - Final record count: {len(df)}")
            
            logger.info("Transformation complete")
            return self.transformed_data
        
        except Exception as e:
            logger.error(f"Error during transformation: {str(e)}")
            raise
    
    def load_to_csv(self, output_dir='output'):
        """Load: Save transformed data to CSV files"""
        try:
            logger.info(f"Loading data to CSV format in {output_dir}")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            if not self.transformed_data:
                raise ValueError("No transformed data to load. Run transform() first.")
            
            for sheet_name, df in self.transformed_data.items():
                output_file = os.path.join(output_dir, f"{sheet_name}_{self.timestamp}.csv")
                df.to_csv(output_file, index=False, encoding='utf-8')
                logger.info(f"  - Loaded {sheet_name} to {output_file} ({len(df)} records)")
            
            logger.info("CSV loading complete")
        
        except Exception as e:
            logger.error(f"Error during CSV load: {str(e)}")
            raise
    
    def load_to_json(self, output_dir='output'):
        """Load: Save transformed data to JSON files"""
        try:
            logger.info(f"Loading data to JSON format in {output_dir}")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            if not self.transformed_data:
                raise ValueError("No transformed data to load. Run transform() first.")
            
            for sheet_name, df in self.transformed_data.items():
                output_file = os.path.join(output_dir, f"{sheet_name}_{self.timestamp}.json")
                df.to_json(output_file, orient='records', indent=2, force_ascii=False)
                logger.info(f"  - Loaded {sheet_name} to {output_file} ({len(df)} records)")
            
            logger.info("JSON loading complete")
        
        except Exception as e:
            logger.error(f"Error during JSON load: {str(e)}")
            raise
    
    def load_to_excel(self, output_file='output/transformed_data.xlsx'):
        """Load: Save all transformed data to a single Excel file with multiple sheets"""
        try:
            logger.info(f"Loading data to Excel format: {output_file}")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            if not self.transformed_data:
                raise ValueError("No transformed data to load. Run transform() first.")
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for sheet_name, df in self.transformed_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"  - Loaded {sheet_name} to Excel ({len(df)} records)")
            
            logger.info(f"Excel loading complete: {output_file}")
        
        except Exception as e:
            logger.error(f"Error during Excel load: {str(e)}")
            raise
    
    def get_statistics(self):
        """Get statistics about the transformed data"""
        stats = {}
        for sheet_name, df in self.transformed_data.items():
            stats[sheet_name] = {
                'total_records': len(df),
                'total_columns': len(df.columns),
                'columns': df.columns.tolist(),
                'memory_usage': df.memory_usage(deep=True).sum() / 1024**2  # MB
            }
        return stats
    
    def run_full_pipeline(self, output_formats=['csv', 'json', 'excel']):
        """Run the complete ETL pipeline"""
        try:
            logger.info("=" * 50)
            logger.info("Starting ETL Pipeline")
            logger.info("=" * 50)
            
            # Step 1: Extract
            self.extract()
            
            # Step 2: Transform
            self.transform()
            
            # Step 3: Load to requested formats
            if 'csv' in output_formats:
                self.load_to_csv()
            
            if 'json' in output_formats:
                self.load_to_json()
            
            if 'excel' in output_formats:
                self.load_to_excel()
            
            # Display statistics
            logger.info("\n" + "=" * 50)
            logger.info("Pipeline Statistics")
            logger.info("=" * 50)
            stats = self.get_statistics()
            for sheet_name, sheet_stats in stats.items():
                logger.info(f"\n{sheet_name}:")
                logger.info(f"  Total Records: {sheet_stats['total_records']}")
                logger.info(f"  Total Columns: {sheet_stats['total_columns']}")
                logger.info(f"  Memory Usage: {sheet_stats['memory_usage']:.2f} MB")
            
            logger.info("\n" + "=" * 50)
            logger.info("ETL Pipeline Completed Successfully!")
            logger.info("=" * 50)
        
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise


if __name__ == "__main__":
    # Run the ETL pipeline
    json_file = 'sttm.json'
    
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found!")
        exit(1)
    
    pipeline = ETLPipeline(json_file)
    
    # Run full pipeline with all output formats
    pipeline.run_full_pipeline(output_formats=['csv', 'json', 'excel'])

"""
Data Quality Validator for MSRB SCD Type 2 Loader
Checks: Nulls in PK, Special Characters, Threshold Variance, Datatype Mismatches
"""

import pandas as pd
import re
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Comprehensive data quality checks for MSRB data"""
    
    # Allowed special characters (minimal set)
    ALLOWED_SPECIAL_CHARS = r"[^a-zA-Z0-9\s\-\.\,\(\)\&\'\\/]"
    
    # Expected data types for each column
    EXPECTED_TYPES = {
        'MSRB_ID': 'string',
        'Firm Name': 'string',
        'State': 'string',
        'Registrant Type': 'string'
    }
    
    # Threshold for record count variance (10%)
    RECORD_COUNT_THRESHOLD = 0.10
    
    def __init__(self, previous_count: int = None):
        """
        Initialize validator
        
        Args:
            previous_count: Record count from previous load (for threshold check)
        """
        self.previous_count = previous_count
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0
    
    def validate_dataframe(self, df: pd.DataFrame, source_file: str) -> Dict[str, Any]:
        """
        Run all validations on dataframe
        
        Args:
            df: Input dataframe
            source_file: Source file name
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"DATA QUALITY VALIDATION - {source_file}")
        logger.info(f"{'='*80}")
        
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0
        
        # Run all checks
        self._check_null_pk(df)
        self._check_special_characters(df)
        self._check_record_count_threshold(df)
        self._check_datatype_consistency(df)
        
        # Log summary
        self._log_summary()
        
        is_valid = len(self.errors) == 0
        
        return {
            'is_valid': is_valid,
            'total_records': len(df),
            'errors': self.errors,
            'warnings': self.warnings,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    def _check_null_pk(self, df: pd.DataFrame):
        """Check 1: Null values in Primary Key (MSRB ID)"""
        logger.info("\n[CHECK 1] Validating Primary Key (MSRB ID) - No Nulls Allowed")
        logger.info("-" * 80)
        
        null_count = df['MSRB ID'].isnull().sum()
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
        
        if null_count > 0:
            self.checks_failed += 1
            error_msg = f"ERROR: NULL values found in MSRB_ID: {null_count} records ({null_pct:.2f}%)"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            # Get indices of null rows
            null_indices = df[df['MSRB ID'].isnull()].index.tolist()
            logger.error(f"   Affected rows: {null_indices[:10]}{'...' if len(null_indices) > 10 else ''}")
        else:
            self.checks_passed += 1
            logger.info(f"PASS: No null values in MSRB_ID ({len(df)} records)")
    
    def _check_special_characters(self, df: pd.DataFrame):
        """Check 2: Special characters validation"""
        logger.info("\n[CHECK 2] Validating Special Characters")
        logger.info("-" * 80)
        
        special_char_issues = []
        
        # Check each string column
        for col in df.select_dtypes(include=['object']).columns:
            invalid_rows = []
            
            for idx, value in df[col].items():
                if pd.isna(value):
                    continue
                    
                value_str = str(value)
                # Look for disallowed special characters
                if re.search(self.ALLOWED_SPECIAL_CHARS, value_str):
                    invalid_rows.append({
                        'row': idx,
                        'column': col,
                        'value': value_str[:50]  # Truncate for display
                    })
            
            if invalid_rows:
                self.checks_failed += 1
                error_msg = f"SPECIAL_CHAR_ERROR in {col}: {len(invalid_rows)} records"
                logger.error(error_msg)
                self.errors.append(error_msg)
                
                # Show first few examples
                for issue in invalid_rows[:3]:
                    logger.error(f"   Row {issue['row']}: {issue['value']}")
                if len(invalid_rows) > 3:
                    logger.error(f"   ... and {len(invalid_rows) - 3} more")
                
                special_char_issues.extend(invalid_rows)
        
        if not special_char_issues:
            self.checks_passed += 1
            logger.info("PASS: No invalid special characters found")
    
    def _check_record_count_threshold(self, df: pd.DataFrame):
        """Check 3: Record count variance threshold (>10% not allowed)"""
        logger.info("\n[CHECK 3] Validating Record Count Threshold (10% Max Variance)")
        logger.info("-" * 80)
        
        current_count = len(df)
        
        if self.previous_count is None or self.previous_count == 0:
            self.checks_passed += 1
            logger.info(f"INFO: First load - Setting baseline: {current_count} records")
            logger.info("PASS: No previous load to compare (baseline set)")
            return
        
        # Calculate variance
        variance = abs(current_count - self.previous_count) / self.previous_count
        variance_pct = variance * 100
        
        logger.info(f"Previous load: {self.previous_count} records")
        logger.info(f"Current load:  {current_count} records")
        logger.info(f"Variance:      {variance_pct:.2f}%")
        logger.info(f"Threshold:     {self.RECORD_COUNT_THRESHOLD * 100}%")
        
        if variance > self.RECORD_COUNT_THRESHOLD:
            self.checks_failed += 1
            error_msg = f"ERROR: Record count variance exceeds threshold: {variance_pct:.2f}% > {self.RECORD_COUNT_THRESHOLD * 100}%"
            logger.error(error_msg)
            self.errors.append(error_msg)
            logger.error(f"   Expected range: {int(self.previous_count * 0.9)}-{int(self.previous_count * 1.1)}")
            logger.error(f"   Actual count: {current_count}")
        else:
            self.checks_passed += 1
            logger.info(f"PASS: Variance within acceptable range ({variance_pct:.2f}%)")
    
    def _check_datatype_consistency(self, df: pd.DataFrame):
        """Check 4: Data type consistency validation"""
        logger.info("\n[CHECK 4] Validating Data Type Consistency")
        logger.info("-" * 80)
        
        datatype_issues = []
        
        for col in df.columns:
            if col not in self.EXPECTED_TYPES:
                continue
            
            expected_type = self.EXPECTED_TYPES[col]
            actual_type = df[col].dtype
            
            logger.info(f"\nColumn: {col}")
            logger.info(f"  Expected: {expected_type}")
            logger.info(f"  Actual: {actual_type}")
            
            # Check for type mismatches
            if expected_type == 'string':
                # For string columns, check if all non-null values are strings
                non_null_mask = df[col].notna()
                non_string_count = 0
                
                for val in df[col][non_null_mask]:
                    if not isinstance(val, str):
                        # Try to convert, but flag if it fails
                        try:
                            str(val)
                        except:
                            non_string_count += 1
                
                if non_string_count > 0:
                    self.checks_failed += 1
                    error_msg = f"ERROR: Data type mismatch in {col}: {non_string_count} non-string values found"
                    logger.error(f"  {error_msg}")
                    self.errors.append(error_msg)
                    datatype_issues.append({
                        'column': col,
                        'expected': expected_type,
                        'issues': non_string_count
                    })
                else:
                    self.checks_passed += 1
                    logger.info(f"  PASS: All values convertible to string")
            
            elif expected_type == 'numeric':
                # For numeric columns
                if not pd.api.types.is_numeric_dtype(actual_type):
                    self.checks_failed += 1
                    error_msg = f"ERROR: Data type mismatch in {col}: expected numeric, got {actual_type}"
                    logger.error(f"  {error_msg}")
                    self.errors.append(error_msg)
                    datatype_issues.append({
                        'column': col,
                        'expected': expected_type,
                        'actual': str(actual_type)
                    })
                else:
                    self.checks_passed += 1
                    logger.info(f"  PASS: Correct numeric type")
        
        if not datatype_issues:
            logger.info("\nPASS: All data types consistent")
    
    def _log_summary(self):
        """Log validation summary"""
        logger.info(f"\n{'='*80}")
        logger.info("DATA QUALITY VALIDATION SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Checks Passed: {self.checks_passed}")
        logger.info(f"Checks Failed: {self.checks_failed}")
        logger.info(f"Errors Found:  {len(self.errors)}")
        logger.info(f"Warnings Found: {len(self.warnings)}")
        
        if self.errors:
            logger.error("\n[ERRORS]")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
        
        if self.warnings:
            logger.warning("\n[WARNINGS]")
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"  {i}. {warning}")
        
        status = "PASSED" if len(self.errors) == 0 else "FAILED"
        logger.info(f"\nOverall Status: {status}")
        logger.info(f"{'='*80}\n")
    
    def export_validation_report(self, output_file: str, validation_result: Dict[str, Any]):
        """Export validation report to CSV"""
        report_data = {
            'Timestamp': datetime.now().isoformat(),
            'Total Records': validation_result['total_records'],
            'Checks Passed': validation_result['checks_passed'],
            'Checks Failed': validation_result['checks_failed'],
            'Errors Found': validation_result['error_count'],
            'Warnings Found': validation_result['warning_count'],
            'Status': 'PASS' if validation_result['is_valid'] else 'FAIL'
        }
        
        # Convert to dataframe and save
        report_df = pd.DataFrame([report_data])
        report_df.to_csv(output_file, index=False)
        logger.info(f"Validation report exported to {output_file}")
        
        return report_df


class DataQualityReporter:
    """Generate detailed data quality reports"""
    
    @staticmethod
    def generate_report(validation_results: List[Dict[str, Any]], 
                       output_dir: str = './output'):
        """Generate comprehensive data quality report"""
        
        Path(output_dir).mkdir(exist_ok=True)
        report_file = f"{output_dir}/data_quality_report.csv"
        
        report_data = []
        for result in validation_results:
            report_data.append({
                'Check': result.get('check_name', 'Unknown'),
                'Status': 'PASS' if result.get('is_valid', False) else 'FAIL',
                'Total Records': result.get('total_records', 0),
                'Errors': result.get('error_count', 0),
                'Warnings': result.get('warning_count', 0),
                'Timestamp': datetime.now().isoformat()
            })
        
        report_df = pd.DataFrame(report_data)
        report_df.to_csv(report_file, index=False)
        logger.info(f"Quality report saved to {report_file}")
        
        return report_df


def validate_before_load(csv_file: str, previous_count: int = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate CSV file before loading
    
    Args:
        csv_file: Path to CSV file
        previous_count: Record count from previous load
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    try:
        df = pd.read_csv(csv_file)
        
        validator = DataQualityValidator(previous_count)
        result = validator.validate_dataframe(df, csv_file)
        
        return result['is_valid'], result
    
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return False, {
            'is_valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'total_records': 0
        }

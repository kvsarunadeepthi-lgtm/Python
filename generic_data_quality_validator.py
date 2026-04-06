"""
Generic Data Quality Validator - ConfigJSON-based CSV Validation
Validates any CSV file against configurable data quality checks defined in JSON
"""

import json
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class CheckType(Enum):
    """Data quality check types"""
    NULL_CHECK = "null_check"
    UNIQUENESS_CHECK = "uniqueness_check"
    NUMERIC_ONLY_CHECK = "numeric_only_check"
    MAX_LENGTH_CHECK = "max_length_check"


@dataclass
class ValidationError:
    """Represents a single validation error"""
    column_name: str
    check_type: str
    row_indices: List[int]
    error_count: int
    error_message: str
    sample_values: List[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CheckResult:
    """Result of a single data quality check"""
    column_name: str
    check_type: str
    passed: bool
    error_count: int
    total_records: int
    error_message: str = ""
    row_indices: List[int] = None
    sample_values: List[Any] = None


# ============================================================================
# GENERIC DATA QUALITY VALIDATOR
# ============================================================================

class GenericDataQualityValidator:
    """
    Configurable validator for CSV files based on JSON configuration
    Supports: Null checks, Uniqueness, Numeric validation, Max length
    """
    
    def __init__(self, config_file: str):
        """
        Initialize validator with configuration file
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.validation_results: List[CheckResult] = []
        self.dataframe: Optional[pd.DataFrame] = None
        self.total_records = 0
        
    def _load_config(self) -> Dict:
        """Load and validate configuration JSON"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_file}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def validate_csv(self, csv_file: str, columns_to_validate: int = 4) -> Tuple[bool, List[CheckResult]]:
        """
        Main validation method - validates first N columns of CSV against configuration
        
        Args:
            csv_file: Path to CSV file to validate
            columns_to_validate: Number of columns to validate from the start (default: 4)
            
        Returns:
            Tuple of (overall_passed: bool, results: List[CheckResult])
        """
        try:
            # Load CSV
            self.dataframe = pd.read_csv(csv_file)
            self.total_records = len(self.dataframe)
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"STARTING DATA QUALITY VALIDATION")
            logger.info(f"{'=' * 80}")
            logger.info(f"File: {csv_file}")
            logger.info(f"Total Records: {self.total_records}")
            logger.info(f"Total Columns: {len(self.dataframe.columns)}")
            logger.info(f"{'=' * 80}\n")
            
            # Reset results
            self.validation_results = []
            
            # Get the first N columns from the CSV
            columns_to_check = self.dataframe.columns[:columns_to_validate].tolist()
            logger.info(f"Validating first {columns_to_validate} columns: {columns_to_check}\n")
            
            # Get column checks from configuration
            column_checks_config = self.config.get('column_checks', [])
            
            # Validate each column by position
            for col_position, column_name in enumerate(columns_to_check):
                logger.info(f"Processing Column {col_position} ({column_name}):")
                
                # Find checks for this column position
                col_check_config = None
                for check_config in column_checks_config:
                    if check_config.get('column_position') == col_position:
                        col_check_config = check_config
                        break
                
                if col_check_config is None:
                    logger.info(f"  No checks configured for column position {col_position}. Skipping.\n")
                    continue
                
                # Prepare column config for check methods
                prepared_config = {
                    'column_name': column_name,
                    'column_position': col_position,
                    'checks': col_check_config.get('checks', {})
                }
                
                # Run all enabled checks for this column
                checks = prepared_config.get('checks', {})
                
                if checks.get('null_check', {}).get('enabled'):
                    self._validate_null_check(prepared_config)
                
                if checks.get('uniqueness_check', {}).get('enabled'):
                    self._validate_uniqueness_check(prepared_config)
                
                if checks.get('numeric_only_check', {}).get('enabled'):
                    self._validate_numeric_only_check(prepared_config)
                
                if checks.get('max_length_check', {}).get('enabled'):
                    self._validate_max_length_check(prepared_config)
                
                if checks.get('pattern_match_check', {}).get('enabled'):
                    self._validate_pattern_match_check(prepared_config)
                
                if checks.get('range_check', {}).get('enabled'):
                    self._validate_range_check(prepared_config)
                
                if checks.get('enum_check', {}).get('enabled'):
                    self._validate_enum_check(prepared_config)
            
            # Determine overall pass/fail
            overall_passed = all(result.passed for result in self.validation_results)
            
            return overall_passed, self.validation_results
            
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            raise
    
    # ========================================================================
    # INDIVIDUAL CHECK METHODS
    # ========================================================================
    
    def _validate_null_check(self, col_config: Dict) -> None:
        """Check for null/empty values"""
        column_name = col_config['column_name']
        check_config = col_config['checks']['null_check']
        allow_null = check_config.get('allow_null', False)
        
        # Check for null and empty values
        null_mask = (self.dataframe[column_name].isnull()) | (self.dataframe[column_name].astype(str).str.strip() == '')
        null_indices = self.dataframe[null_mask].index.tolist()
        error_count = len(null_indices)
        
        passed = error_count == 0 if not allow_null else True
        
        if error_count > 0:
            error_msg = f"Found {error_count} null/empty values" if not allow_null else f"Found {error_count} null/empty values (allowed)"
            sample_values = [f"Row {idx}" for idx in null_indices[:5]]
        else:
            error_msg = "✓ No null/empty values found"
            sample_values = []
        
        logger.info(f"[NULL CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type=CheckType.NULL_CHECK.value,
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=null_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_uniqueness_check(self, col_config: Dict) -> None:
        """Check for duplicate values"""
        column_name = col_config['column_name']
        
        # Find duplicates
        duplicates_mask = self.dataframe[column_name].duplicated(keep=False)
        duplicate_indices = self.dataframe[duplicates_mask].index.tolist()
        duplicate_values = self.dataframe[duplicates_mask][column_name].unique().tolist()
        
        # Count duplicate occurrences
        error_count = 0
        for val in duplicate_values:
            count = (self.dataframe[column_name] == val).sum()
            if count > 1:
                error_count += count
        
        passed = error_count == 0
        
        if error_count > 0:
            error_msg = f"Found {error_count} non-unique values ({len(duplicate_values)} duplicates)"
            sample_values = [f"Value: {v} (appears {(self.dataframe[column_name] == v).sum()}x)" 
                           for v in duplicate_values[:5]]
        else:
            error_msg = "✓ All values are unique"
            sample_values = []
        
        logger.info(f"[UNIQUENESS CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type=CheckType.UNIQUENESS_CHECK.value,
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=duplicate_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_numeric_only_check(self, col_config: Dict) -> None:
        """Check if column contains only numeric values"""
        column_name = col_config['column_name']
        
        error_indices = []
        for idx, val in self.dataframe[column_name].items():
            if pd.isna(val):
                continue
            try:
                float(str(val).strip())
            except ValueError:
                error_indices.append(idx)
        
        error_count = len(error_indices)
        passed = error_count == 0
        
        if error_count > 0:
            error_msg = f"Found {error_count} non-numeric values"
            sample_values = [self.dataframe.loc[idx, column_name] for idx in error_indices[:5]]
        else:
            error_msg = "✓ All values are numeric"
            sample_values = []
        
        logger.info(f"[NUMERIC CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type=CheckType.NUMERIC_ONLY_CHECK.value,
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=error_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_max_length_check(self, col_config: Dict) -> None:
        """Check if string values exceed maximum length"""
        column_name = col_config['column_name']
        max_length = col_config['checks']['max_length_check'].get('max_length', 100)
        
        error_indices = []
        error_values = []
        
        for idx, val in self.dataframe[column_name].items():
            if pd.isna(val):
                continue
            str_val = str(val)
            if len(str_val) > max_length:
                error_indices.append(idx)
                error_values.append((str_val[:50] + "..." if len(str_val) > 50 else str_val, len(str_val)))
        
        error_count = len(error_indices)
        passed = error_count == 0
        
        if error_count > 0:
            error_msg = f"Found {error_count} values exceeding max length ({max_length})"
            sample_values = [f"Length {length}: {val}" for val, length in error_values[:5]]
        else:
            error_msg = f"✓ All values within max length ({max_length})"
            sample_values = []
        
        logger.info(f"[MAX LENGTH CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type=CheckType.MAX_LENGTH_CHECK.value,
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=error_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_pattern_match_check(self, col_config: Dict) -> None:
        """Check if values match a regex pattern"""
        import re
        column_name = col_config['column_name']
        pattern = col_config['checks']['pattern_match_check'].get('pattern', '.*')
        
        error_indices = []
        error_values = []
        
        for idx, val in self.dataframe[column_name].items():
            if pd.isna(val):
                continue
            str_val = str(val)
            if not re.match(pattern, str_val):
                error_indices.append(idx)
                error_values.append(str_val[:50])
        
        error_count = len(error_indices)
        passed = error_count == 0
        
        if error_count > 0:
            error_msg = f"Found {error_count} values not matching pattern: {pattern}"
            sample_values = error_values[:5]
        else:
            error_msg = f"✓ All values match pattern: {pattern}"
            sample_values = []
        
        logger.info(f"[PATTERN MATCH CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type="pattern_match_check",
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=error_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_range_check(self, col_config: Dict) -> None:
        """Check if numeric values are within a specified range"""
        column_name = col_config['column_name']
        min_value = col_config['checks']['range_check'].get('min_value')
        max_value = col_config['checks']['range_check'].get('max_value')
        
        error_indices = []
        error_values = []
        
        for idx, val in self.dataframe[column_name].items():
            if pd.isna(val):
                continue
            try:
                num_val = float(val)
                if (min_value is not None and num_val < min_value) or (max_value is not None and num_val > max_value):
                    error_indices.append(idx)
                    error_values.append(num_val)
            except (ValueError, TypeError):
                continue
        
        error_count = len(error_indices)
        passed = error_count == 0
        
        range_str = f"[{min_value}, {max_value}]"
        if error_count > 0:
            error_msg = f"Found {error_count} values outside range {range_str}"
            sample_values = [str(v) for v in error_values[:5]]
        else:
            error_msg = f"✓ All values within range {range_str}"
            sample_values = []
        
        logger.info(f"[RANGE CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type="range_check",
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=error_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    def _validate_enum_check(self, col_config: Dict) -> None:
        """Check if values are within an allowed list"""
        column_name = col_config['column_name']
        allowed_values = col_config['checks']['enum_check'].get('allowed_values', [])
        
        error_indices = []
        error_values = []
        
        for idx, val in self.dataframe[column_name].items():
            if pd.isna(val):
                continue
            str_val = str(val).strip()
            if str_val not in allowed_values:
                error_indices.append(idx)
                error_values.append(str_val)
        
        error_count = len(error_indices)
        passed = error_count == 0
        
        if error_count > 0:
            error_msg = f"Found {error_count} values not in allowed list: {allowed_values}"
            sample_values = list(set(error_values[:5]))
        else:
            error_msg = f"✓ All values are in allowed list"
            sample_values = []
        
        logger.info(f"[ENUM CHECK] {column_name}: {error_msg}")
        
        result = CheckResult(
            column_name=column_name,
            check_type="enum_check",
            passed=passed,
            error_count=error_count,
            total_records=self.total_records,
            error_message=error_msg,
            row_indices=error_indices[:self.config['reporting']['max_error_samples']],
            sample_values=sample_values
        )
        self.validation_results.append(result)
    
    # ========================================================================
    # REPORTING METHODS
    # ========================================================================
    
    def generate_report(self, output_dir: str = "./output") -> str:
        """
        Generate validation report and save to CSV
        
        Args:
            output_dir: Directory to save reports
            
        Returns:
            Path to generated report file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Prepare report data
        report_data = []
        for result in self.validation_results:
            # Avoid division by zero
            pass_rate = 0 if result.total_records == 0 else round((1 - result.error_count / result.total_records) * 100, 2)
            report_data.append({
                'Column': result.column_name,
                'Check Type': result.check_type,
                'Status': 'PASS' if result.passed else 'FAIL',
                'Error Count': result.error_count,
                'Total Records': result.total_records,
                'Pass Rate %': pass_rate,
                'Error Message': result.error_message,
                'Sample Row Indices': str(result.row_indices) if result.row_indices else "N/A",
                'Sample Values': str(result.sample_values) if result.sample_values else "N/A"
            })
        
        # Create DataFrame and save
        report_df = pd.DataFrame(report_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{output_dir}/data_quality_validation_{timestamp}.csv"
        report_df.to_csv(report_file, index=False)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"VALIDATION REPORT GENERATED")
        logger.info(f"{'=' * 80}")
        logger.info(f"Report saved to: {report_file}\n")
        
        return report_file
    
    def print_summary(self) -> None:
        """Print validation summary to console"""
        total_checks = len(self.validation_results)
        passed_checks = sum(1 for r in self.validation_results if r.passed)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"VALIDATION SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total Checks Run: {total_checks}")
        logger.info(f"Passed: {passed_checks}")
        logger.info(f"Failed: {total_checks - passed_checks}")
        
        # Avoid division by zero
        if total_checks > 0:
            success_rate = round(passed_checks / total_checks * 100, 2)
            logger.info(f"Success Rate: {success_rate}%")
        else:
            logger.warning(f"No checks were configured or run!")
            logger.warning(f"Please verify your JSON configuration has column_checks defined.")
        
        logger.info(f"{'=' * 80}\n")
        
        # Detailed results
        for result in self.validation_results:
            status_icon = "✓" if result.passed else "✗"
            logger.info(f"{status_icon} {result.column_name} - {result.check_type}: {result.error_message}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def main():
    """Main function - prompts user for input files and executes validation"""
    print("\n" + "=" * 80)
    print("GENERIC DATA QUALITY VALIDATOR")
    print("=" * 80)
    
    # Prompt for JSON configuration file
    while True:
        config_file = input("\nEnter the path to the JSON configuration file: ").strip()
        if not config_file:
            print("Error: Configuration file path cannot be empty.")
            continue
        if not Path(config_file).exists():
            print(f"Error: Configuration file not found: {config_file}")
            continue
        break
    
    # Prompt for CSV file to validate
    while True:
        csv_file = input("Enter the path to the CSV file to validate: ").strip()
        if not csv_file:
            print("Error: CSV file path cannot be empty.")
            continue
        if not Path(csv_file).exists():
            print(f"Error: CSV file not found: {csv_file}")
            continue
        break
    
    # Initialize validator and run validation
    try:
        print(f"\nInitializing validator with config: {config_file}")
        validator = GenericDataQualityValidator(config_file)
        
        print(f"Validating CSV file: {csv_file}")
        overall_passed, results = validator.validate_csv(csv_file)
        
        # Print summary
        validator.print_summary()
        
        # Generate detailed report
        report_file = validator.generate_report()
        print(f"Report saved to: {report_file}")
        
        # Check overall status
        if overall_passed:
            logger.info("\n✓ All validation checks PASSED!")
        else:
            logger.info("\n✗ Some validation checks FAILED!")
            logger.info("Review the report for details.")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")


if __name__ == "__main__":
    main()

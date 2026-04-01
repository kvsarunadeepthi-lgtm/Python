"""
Generic Data Quality Validator Framework for MSRB Data
Flexible validation engine with configurable rules for any file/columns
"""

import pandas as pd
import re
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any, Callable
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION RULE TYPES & CLASSES
# ============================================================================

class RuleType(Enum):
    """Enumeration of all available validation rule types"""
    NOT_NULL = "NOT_NULL"
    NOT_EMPTY = "NOT_EMPTY"
    DATA_TYPE = "DATA_TYPE"
    LENGTH_MIN = "LENGTH_MIN"
    LENGTH_MAX = "LENGTH_MAX"
    LENGTH_EXACT = "LENGTH_EXACT"
    REGEX = "REGEX"
    UNIQUE = "UNIQUE"
    ALLOWED_VALUES = "ALLOWED_VALUES"
    NUMERIC_ONLY = "NUMERIC_ONLY"
    NO_NUMERIC_ONLY = "NO_NUMERIC_ONLY"
    NO_LEADING_TRAILING_SPACES = "NO_LEADING_TRAILING_SPACES"
    CUSTOM = "CUSTOM"


class ValidationRule:
    """
    Individual validation rule that can be applied to a column
    
    Attributes:
        rule_type: Type of validation (from RuleType enum)
        parameters: Dict with rule-specific parameters
        error_message: Custom error message (optional)
    """
    
    def __init__(self, 
                 rule_type: RuleType,
                 parameters: Dict[str, Any] = None,
                 error_message: str = None):
        """Initialize a validation rule"""
        self.rule_type = rule_type
        self.parameters = parameters or {}
        self.error_message = error_message
    
    def validate(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """
        Validate a single value against this rule
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.rule_type == RuleType.NOT_NULL:
            return self._check_not_null(value, column_name)
        
        elif self.rule_type == RuleType.NOT_EMPTY:
            return self._check_not_empty(value, column_name)
        
        elif self.rule_type == RuleType.DATA_TYPE:
            return self._check_data_type(value, column_name)
        
        elif self.rule_type == RuleType.LENGTH_MIN:
            return self._check_length_min(value, column_name)
        
        elif self.rule_type == RuleType.LENGTH_MAX:
            return self._check_length_max(value, column_name)
        
        elif self.rule_type == RuleType.LENGTH_EXACT:
            return self._check_length_exact(value, column_name)
        
        elif self.rule_type == RuleType.REGEX:
            return self._check_regex(value, column_name)
        
        elif self.rule_type == RuleType.NUMERIC_ONLY:
            return self._check_numeric_only(value, column_name)
        
        elif self.rule_type == RuleType.NO_NUMERIC_ONLY:
            return self._check_no_numeric_only(value, column_name)
        
        elif self.rule_type == RuleType.NO_LEADING_TRAILING_SPACES:
            return self._check_no_leading_trailing_spaces(value, column_name)
        
        elif self.rule_type == RuleType.ALLOWED_VALUES:
            return self._check_allowed_values(value, column_name)
        
        elif self.rule_type == RuleType.CUSTOM:
            return self._check_custom(value, column_name)
        
        else:
            return True, ""
    
    # ========== Individual Check Methods ==========
    
    def _check_not_null(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value is not NULL/None"""
        if pd.isna(value):
            msg = self.error_message or f"{column_name}: NULL value not allowed"
            return False, msg
        return True, ""
    
    def _check_not_empty(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value is not empty string or whitespace"""
        if pd.isna(value):
            return True, ""  # NOT_NULL handles NULL check
        
        value_str = str(value).strip()
        if value_str == "":
            msg = self.error_message or f"{column_name}: Empty/blank value not allowed"
            return False, msg
        return True, ""
    
    def _check_data_type(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value matches expected data type"""
        if pd.isna(value):
            return True, ""  # NOT_NULL handles NULL check
        
        expected_type = self.parameters.get('type', 'str')
        
        try:
            if expected_type == 'string' or expected_type == 'str':
                # Any value can be converted to string
                return True, ""
            
            elif expected_type == 'integer' or expected_type == 'int':
                int(value)
                return True, ""
            
            elif expected_type == 'numeric' or expected_type == 'number':
                float(value)
                return True, ""
            
            else:
                return True, ""
        
        except (ValueError, TypeError):
            msg = self.error_message or f"{column_name}: Invalid data type (expected {expected_type})"
            return False, msg
    
    def _check_length_min(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value length >= minimum"""
        if pd.isna(value):
            return True, ""
        
        min_length = self.parameters.get('min_length', 0)
        value_length = len(str(value))
        
        if value_length < min_length:
            msg = self.error_message or f"{column_name}: Length {value_length} is less than minimum {min_length}"
            return False, msg
        return True, ""
    
    def _check_length_max(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value length <= maximum"""
        if pd.isna(value):
            return True, ""
        
        max_length = self.parameters.get('max_length', 999999)
        value_length = len(str(value))
        
        if value_length > max_length:
            msg = self.error_message or f"{column_name}: Length {value_length} exceeds maximum {max_length}"
            return False, msg
        return True, ""
    
    def _check_length_exact(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value length == exact length"""
        if pd.isna(value):
            return True, ""
        
        exact_length = self.parameters.get('length', 0)
        value_length = len(str(value))
        
        if value_length != exact_length:
            msg = self.error_message or f"{column_name}: Length {value_length} must be exactly {exact_length}"
            return False, msg
        return True, ""
    
    def _check_regex(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value matches regex pattern"""
        if pd.isna(value):
            return True, ""
        
        pattern = self.parameters.get('pattern', '')
        value_str = str(value)
        
        if not re.match(pattern, value_str):
            msg = self.error_message or f"{column_name}: Value '{value_str}' does not match pattern '{pattern}'"
            return False, msg
        return True, ""
    
    def _check_numeric_only(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value contains only digits"""
        if pd.isna(value):
            return True, ""
        
        value_str = str(value).strip()
        if not value_str.isdigit():
            msg = self.error_message or f"{column_name}: Value '{value_str}' must be numeric only"
            return False, msg
        return True, ""
    
    def _check_no_numeric_only(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value is NOT numeric-only (contains non-digit characters)"""
        if pd.isna(value):
            return True, ""
        
        value_str = str(value).strip()
        if value_str.isdigit():
            msg = self.error_message or f"{column_name}: Value cannot be numeric-only"
            return False, msg
        return True, ""
    
    def _check_no_leading_trailing_spaces(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value has no leading/trailing spaces"""
        if pd.isna(value):
            return True, ""
        
        value_str = str(value)
        if value_str != value_str.strip():
            msg = self.error_message or f"{column_name}: Value has leading/trailing spaces"
            return False, msg
        return True, ""
    
    def _check_allowed_values(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check if value is in the allowed values list"""
        if pd.isna(value):
            return True, ""
        
        allowed_values = self.parameters.get('values', [])
        value_str = str(value).strip()
        
        if value_str not in allowed_values:
            msg = self.error_message or f"{column_name}: Value '{value_str}' not in allowed values"
            return False, msg
        return True, ""
    
    def _check_custom(self, value: Any, column_name: str) -> Tuple[bool, str]:
        """Check using custom validation function"""
        if pd.isna(value):
            return True, ""
        
        custom_func = self.parameters.get('function')
        if not custom_func or not callable(custom_func):
            return True, ""
        
        try:
            is_valid = custom_func(value)
            if not is_valid:
                msg = self.error_message or f"{column_name}: Custom validation failed"
                return False, msg
            return True, ""
        except Exception as e:
            msg = self.error_message or f"{column_name}: Custom validation error: {str(e)}"
            return False, msg


class ColumnDefinition:
    """
    Definition of a column with its validation rules
    
    Attributes:
        name: Column name (must match CSV header)
        display_name: Human-readable column name
        data_type: Expected data type (string, integer, etc.)
        rules: List of ValidationRule objects to apply
    """
    
    def __init__(self,
                 name: str,
                 display_name: str,
                 data_type: str = 'string',
                 rules: List[ValidationRule] = None):
        """Initialize column definition"""
        self.name = name
        self.display_name = display_name
        self.data_type = data_type
        self.rules = rules or []
    
    def add_rule(self, rule: ValidationRule) -> 'ColumnDefinition':
        """Add a validation rule to this column (fluent interface)"""
        self.rules.append(rule)
        return self
    
    def validate(self, value: Any) -> Tuple[bool, List[str]]:
        """
        Validate a value against all rules for this column
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for rule in self.rules:
            is_valid, error_msg = rule.validate(value, self.display_name)
            if not is_valid:
                errors.append(error_msg)
        
        return len(errors) == 0, errors


# ============================================================================
# MAIN VALIDATOR CLASS
# ============================================================================

class GenericDataQualityValidator:
    """
    Generic data quality validator that applies configurable rules
    
    Key Features:
    - Applies column-specific rules
    - Tracks global rules (e.g., uniqueness across rows)
    - Provides detailed error reporting
    - Supports custom validation functions
    """
    
    def __init__(self, column_definitions: Dict[str, ColumnDefinition]):
        """
        Initialize validator with column definitions
        
        Args:
            column_definitions: Dict mapping column names to ColumnDefinition objects
        """
        self.column_definitions = column_definitions
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0
        self.check_results = []
        self.detailed_errors = []  # Track row-level errors
    
    def validate_dataframe(self, df: pd.DataFrame, source_file: str) -> Dict[str, Any]:
        """
        Run all validations on dataframe
        
        Args:
            df: Input dataframe to validate
            source_file: Source file name (for logging)
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"GENERIC DATA QUALITY VALIDATION - {source_file}")
        logger.info(f"{'='*80}")
        
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0
        self.check_results = []
        self.detailed_errors = []
        
        # Verify all required columns exist
        self._check_column_existence(df)
        
        # Run row-level validations
        self._validate_rows(df)
        
        # Run table-level validations (e.g., uniqueness)
        self._validate_table_level(df)
        
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
            'warning_count': len(self.warnings),
            'check_results': self.check_results,
            'detailed_errors': self.detailed_errors
        }
    
    def _check_column_existence(self, df: pd.DataFrame):
        """Verify all required columns exist in dataframe"""
        logger.info("\n[SCHEMA CHECK] Verifying required columns")
        logger.info("-" * 80)
        
        missing_columns = []
        for col_name in self.column_definitions.keys():
            if col_name not in df.columns:
                missing_columns.append(col_name)
        
        if missing_columns:
            self.checks_failed += 1
            error_msg = f"ERROR: Missing required columns: {', '.join(missing_columns)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            self.check_results.append({
                'check': 'Schema Validation',
                'status': 'FAILED',
                'details': error_msg
            })
        else:
            self.checks_passed += 1
            logger.info(f"PASS: All {len(self.column_definitions)} required columns found")
            self.check_results.append({
                'check': 'Schema Validation',
                'status': 'PASSED',
                'details': f'All {len(self.column_definitions)} columns present'
            })
    
    def _validate_rows(self, df: pd.DataFrame):
        """Validate each row against column rules"""
        logger.info("\n[ROW-LEVEL VALIDATION] Checking each row")
        logger.info("-" * 80)
        
        total_row_errors = 0
        rows_with_errors = set()
        
        # Iterate through dataframe
        for row_idx, row in df.iterrows():
            row_errors = {}
            
            for col_name, col_def in self.column_definitions.items():
                value = row[col_name]
                is_valid, errors = col_def.validate(value)
                
                if not is_valid:
                    row_errors[col_name] = errors
                    total_row_errors += len(errors)
                    rows_with_errors.add(row_idx)
            
            # Log errors for this row
            if row_errors:
                for col_name, col_errors in row_errors.items():
                    for error in col_errors:
                        self.errors.append(f"Row {row_idx}: {error}")
                        self.detailed_errors.append({
                            'row': row_idx,
                            'column': col_name,
                            'value': row[col_name],
                            'error': error
                        })
        
        # Log row validation summary
        if total_row_errors > 0:
            self.checks_failed += 1
            summary = f"Row validation failed: {total_row_errors} error(s) in {len(rows_with_errors)} row(s)"
            logger.error(summary)
            self.check_results.append({
                'check': 'Row-Level Validation',
                'status': 'FAILED',
                'details': summary
            })
            
            # Show sample errors
            logger.error("\nSample errors (first 5):")
            for i, error in enumerate(self.detailed_errors[:5], 1):
                logger.error(f"  {i}. Row {error['row']}, Column '{error['column']}': {error['error']}")
            
            if len(self.detailed_errors) > 5:
                logger.error(f"  ... and {len(self.detailed_errors) - 5} more error(s)")
        else:
            self.checks_passed += 1
            logger.info(f"PASS: All {len(df)} rows passed validation")
            self.check_results.append({
                'check': 'Row-Level Validation',
                'status': 'PASSED',
                'details': f'All {len(df)} rows valid'
            })
    
    def _validate_table_level(self, df: pd.DataFrame):
        """Validate at table level (e.g., uniqueness across all rows)"""
        logger.info("\n[TABLE-LEVEL VALIDATION] Checking uniqueness constraints")
        logger.info("-" * 80)
        
        uniqueness_errors = []
        
        # Check UNIQUE constraint for applicable columns
        for col_name, col_def in self.column_definitions.items():
            has_unique_rule = any(rule.rule_type == RuleType.UNIQUE for rule in col_def.rules)
            
            if has_unique_rule:
                logger.info(f"Checking uniqueness for column '{col_def.display_name}'")
                
                # Find duplicates
                duplicates = df[col_name].duplicated(keep=False)
                duplicate_values = df[duplicates][col_name].unique()
                
                if len(duplicate_values) > 0:
                    error_msg = f"ERROR: Duplicate values found in {col_def.display_name}: {', '.join(map(str, duplicate_values[:3]))}"
                    if len(duplicate_values) > 3:
                        error_msg += f" ... and {len(duplicate_values) - 3} more"
                    
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    uniqueness_errors.append(error_msg)
                    self.check_results.append({
                        'check': f'Uniqueness: {col_def.display_name}',
                        'status': 'FAILED',
                        'details': f'{len(duplicate_values)} duplicate value(s)'
                    })
                    self.checks_failed += 1
                else:
                    logger.info(f"PASS: No duplicates in '{col_def.display_name}'")
                    self.check_results.append({
                        'check': f'Uniqueness: {col_def.display_name}',
                        'status': 'PASSED',
                        'details': 'All values unique'
                    })
                    self.checks_passed += 1
    
    def _log_summary(self):
        """Log validation summary"""
        logger.info(f"\n{'='*80}")
        logger.info("DATA QUALITY VALIDATION SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Checks Passed: {self.checks_passed}")
        logger.info(f"Checks Failed: {self.checks_failed}")
        logger.info(f"Errors Found:  {len(self.errors)}")
        logger.info(f"Detailed Errors: {len(self.detailed_errors)}")
        logger.info(f"Warnings Found: {len(self.warnings)}")
        
        if self.errors:
            logger.error("\n[ERRORS]")
            for i, error in enumerate(self.errors[:10], 1):
                logger.error(f"  {i}. {error}")
            if len(self.errors) > 10:
                logger.error(f"  ... and {len(self.errors) - 10} more error(s)")
        
        status = "PASSED" if len(self.errors) == 0 else "FAILED"
        logger.info(f"\nOverall Status: {status}")
        logger.info(f"{'='*80}\n")


# ============================================================================
# PREDEFINED COLUMN CONFIGURATIONS
# ============================================================================

def get_msrb_column_definitions() -> Dict[str, ColumnDefinition]:
    """
    Get pre-configured column definitions for MSRB registrants data
    
    Returns:
        Dictionary mapping column names to ColumnDefinition objects
    """
    
    definitions = {}
    
    # ===== COL1: Firm Name =====
    definitions['Firm Name'] = (
        ColumnDefinition('Firm Name', 'Firm Name', 'string')
        .add_rule(ValidationRule(RuleType.NOT_NULL))
        .add_rule(ValidationRule(RuleType.NOT_EMPTY))
        .add_rule(ValidationRule(RuleType.LENGTH_MIN, {'min_length': 3}))
        .add_rule(ValidationRule(RuleType.LENGTH_MAX, {'max_length': 100}))
        .add_rule(ValidationRule(RuleType.NO_NUMERIC_ONLY))
        .add_rule(ValidationRule(RuleType.NO_LEADING_TRAILING_SPACES))
        .add_rule(ValidationRule(
            RuleType.REGEX,
            {'pattern': r'^[A-Za-z0-9.,&\- ]+$'},
            'Firm Name: Only alphabets, numbers, spaces, and .,&- allowed'
        ))
    )
    
    # ===== COL2: MSRB ID =====
    definitions['MSRB ID'] = (
        ColumnDefinition('MSRB ID', 'MSRB ID', 'string')
        .add_rule(ValidationRule(RuleType.NOT_NULL))
        .add_rule(ValidationRule(RuleType.NOT_EMPTY))
        .add_rule(ValidationRule(RuleType.LENGTH_EXACT, {'length': 5}))
        .add_rule(ValidationRule(
            RuleType.REGEX,
            {'pattern': r'^[AB]\d{4}$'},
            'MSRB ID: Must be format A or B followed by 4 digits (e.g., A0001)'
        ))
        .add_rule(ValidationRule(RuleType.UNIQUE))
    )
    
    # ===== COL3: State =====
    allowed_states = ["NY", "NJ", "CA", "TX", "FL", "IL", "AZ", "NC", "OH", "MN", 
                      "WI", "AL", "SC", "TN", "RI", "VA", "MO", "MA", "WA", "PA",
                      "MD", "UT", "CO", "KS", "MI", "IN", "AZ", "NV", "NE", "IA",
                      "OR", "WV", "CT", "DE", "GA", "KY", "LA", "ME", "BC", "PR"]
    definitions['State'] = (
        ColumnDefinition('State', 'State', 'string')
        .add_rule(ValidationRule(RuleType.NOT_NULL))
        .add_rule(ValidationRule(RuleType.NOT_EMPTY))
        .add_rule(ValidationRule(RuleType.LENGTH_EXACT, {'length': 2}))
        .add_rule(ValidationRule(
            RuleType.ALLOWED_VALUES,
            {'values': allowed_states},
            f'State: Must be valid US state code'
        ))
    )
    
    # ===== COL4: Registrant Type =====
    allowed_types = ["Broker Dealer", "Broker Dealer/Municipal Advisor", "Bank Dealer"]
    
    definitions['Registrant Type'] = (
        ColumnDefinition('Registrant Type', 'Registrant Type', 'string')
        .add_rule(ValidationRule(RuleType.NOT_NULL))
        .add_rule(ValidationRule(RuleType.NOT_EMPTY))
        .add_rule(ValidationRule(
            RuleType.ALLOWED_VALUES,
            {'values': allowed_types},
            f'Registrant Type: Must be one of {allowed_types}'
        ))
    )
    
    return definitions


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_file(csv_file: str, column_definitions: Dict[str, ColumnDefinition] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a CSV file using generic framework
    
    Args:
        csv_file: Path to CSV file
        column_definitions: Optional custom column definitions (uses MSRB defaults if None)
        
    Returns:
        Tuple of (is_valid, validation_results)
    """
    try:
        # Use MSRB defaults if not provided
        if column_definitions is None:
            column_definitions = get_msrb_column_definitions()
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Validate
        validator = GenericDataQualityValidator(column_definitions)
        result = validator.validate_dataframe(df, csv_file)
        
        return result['is_valid'], result
    
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        return False, {
            'is_valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'warnings': [],
            'total_records': 0,
            'checks_passed': 0,
            'checks_failed': 1,
            'error_count': 1,
            'warning_count': 0,
            'check_results': [],
            'detailed_errors': []
        }


def export_validation_report(validation_result: Dict[str, Any], output_dir: str = './output'):
    """
    Export validation results to CSV reports
    
    Args:
        validation_result: Result dictionary from validate_dataframe()
        output_dir: Output directory path
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    # Summary report
    summary_file = f"{output_dir}/data_quality_report.csv"
    summary_data = {
        'Timestamp': [datetime.now().isoformat()],
        'Total Records': [validation_result['total_records']],
        'Checks Passed': [validation_result['checks_passed']],
        'Checks Failed': [validation_result['checks_failed']],
        'Errors Found': [validation_result['error_count']],
        'Status': ['PASS' if validation_result['is_valid'] else 'FAIL']
    }
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"Validation summary report exported to {summary_file}")
    
    # Detailed check results
    if 'check_results' in validation_result and validation_result['check_results']:
        checks_file = f"{output_dir}/data_quality_report_detailed.csv"
        checks_df = pd.DataFrame(validation_result['check_results'])
        checks_df['Timestamp'] = datetime.now().isoformat()
        checks_df = checks_df[['Timestamp', 'check', 'status', 'details']]
        checks_df.to_csv(checks_file, index=False)
        logger.info(f"Detailed check results exported to {checks_file}")
    
    # Row-level errors (if any)
    if 'detailed_errors' in validation_result and validation_result['detailed_errors']:
        errors_file = f"{output_dir}/data_quality_errors.csv"
        errors_df = pd.DataFrame(validation_result['detailed_errors'])
        errors_df['Timestamp'] = datetime.now().isoformat()
        errors_df = errors_df[['Timestamp', 'row', 'column', 'value', 'error']]
        errors_df.to_csv(errors_file, index=False)
        logger.info(f"Row-level errors exported to {errors_file}")
    
    return summary_file


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data_quality.log')
        ]
    )
    
    # Prompt for file name
    print("\n" + "="*80)
    print("MSRB DATA QUALITY VALIDATOR")
    print("="*80)
    print("\nExpected CSV columns: Firm Name, MSRB ID, State, Registrant Type")
    print("-"*80)
    
    test_file = input("Enter the CSV file path to validate: ").strip()
    
    if not test_file:
        print("ERROR: File path cannot be empty")
        exit(1)
    
    if Path(test_file).exists():
        is_valid, result = validate_file(test_file)
        
        print("\n" + "="*80)
        print("VALIDATION RESULT")
        print("="*80)
        print(f"File: {test_file}")
        print(f"Status: {'PASS' if is_valid else 'FAIL'}")
        print(f"Records: {result['total_records']}")
        print(f"Errors: {result['error_count']}")
        print("="*80)
        
        # Export validation report
        report_file = export_validation_report(result)
        print(f"\nValidation reports saved to ./output/ directory")
        print(f"Summary: {report_file}")
    else:
        print(f"ERROR: File not found: {test_file}")

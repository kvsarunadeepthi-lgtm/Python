import pandas as pd
import json
import os

def convert_xlsx_to_json(xlsx_file, json_file=None):
    """
    Convert an Excel (.xlsx) file to a JSON file.
    
    Args:
        xlsx_file (str): Path to the input Excel file
        json_file (str): Path to the output JSON file. If None, uses xlsx filename with .json extension
    
    Returns:
        str: Path to the created JSON file
    """
    
    # Determine output filename
    if json_file is None:
        json_file = os.path.splitext(xlsx_file)[0] + '.json'
    
    try:
        # Read the Excel file
        print(f"Reading Excel file: {xlsx_file}")
        excel_file = pd.ExcelFile(xlsx_file)
        
        # Check sheet names
        print(f"Sheet names: {excel_file.sheet_names}")
        
        # Convert all sheets to a dictionary
        data = {}
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
            # Convert dataframe to list of dictionaries
            data[sheet_name] = df.to_dict(orient='records')
        
        # Write to JSON file with proper formatting
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted to JSON: {json_file}")
        return json_file
    
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

if __name__ == "__main__":
    # Convert sttm.xlsx to sttm.json
    convert_xlsx_to_json('sttm.xlsx')

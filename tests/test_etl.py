
import unittest
from unittest.mock import patch
import pandas as pd
from etl_semanal import convert_csv_to_parquet
import os

class TestETL(unittest.TestCase):

    def setUp(self):
        # Create dummy CSV files for testing
        self.parquet_dir = os.path.join('data', 'parquet')
        os.makedirs(self.parquet_dir, exist_ok=True)
        
        self.dept_csv_path = os.path.join('data', 'proyecciones_depto_indec.csv')
        self.prov_csv_path = os.path.join('data', 'poblacionxprovinciaindec.csv')

        # Correct data with 9 columns
        dept_data_correct = "col1;col2;col3;col4;col5;col6;col7;col8;col9\n" * 10
        # Malformed data with 10 columns
        dept_data_malformed = "a;b;c;d;e;f;g;h;i;j\n"
        
        with open(self.dept_csv_path, 'w') as f:
            f.write(dept_data_correct)
            f.write(dept_data_malformed)
        
        prov_data = "col1,col2,col3\n" * 5
        with open(self.prov_csv_path, 'w') as f:
            f.write(prov_data)

    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.dept_csv_path):
            os.remove(self.dept_csv_path)
        if os.path.exists(self.prov_csv_path):
            os.remove(self.prov_csv_path)
        
        dept_parquet = os.path.join(self.parquet_dir, 'proyecciones_depto_indec.parquet')
        if os.path.exists(dept_parquet):
            os.remove(dept_parquet)
            
        prov_parquet = os.path.join(self.parquet_dir, 'poblacionxprovinciaindec.parquet')
        if os.path.exists(prov_parquet):
            os.remove(prov_parquet)

    @patch('etl_semanal.load_sql_data')
    def test_convert_csv_to_parquet_handles_bad_lines(self, mock_load_sql_data):
        # Mock the SQL data load to avoid external dependencies
        mock_load_sql_data.return_value = pd.DataFrame()

        # The function should raise a ParserError without the fix
        with self.assertRaises(pd.errors.ParserError):
            # We need to temporarily modify etl_semanal to not handle the error
            # For now, we expect the error to be raised
            convert_csv_to_parquet()

if __name__ == '__main__':
    unittest.main()

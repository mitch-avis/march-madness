"""Unit tests for scraper utility functions."""

from unittest.mock import MagicMock, patch

import pandas as pd
from django.conf import settings
from django.test import TestCase

from scraper.utils import (
    DataScrapingError,
    read_df_from_csv,
    read_write_data,
    write_df_to_csv,
)


class DataScrapingErrorTests(TestCase):
    """Tests for the DataScrapingError class"""

    def test_data_scraping_error_default_message(self):
        """Test that DataScrapingError has the correct default message"""
        # Act
        error = DataScrapingError()

        # Assert
        self.assertEqual(str(error), "Data scraping operation failed")

    def test_data_scraping_error_custom_message(self):
        """Test that DataScrapingError accepts a custom message"""
        # Act
        error = DataScrapingError("Failed to scrape ratings")

        # Assert
        self.assertEqual(str(error), "Failed to scrape ratings")
        self.assertEqual(error.message, "Failed to scrape ratings")


class FileOperationsTests(TestCase):
    """Tests for file reading and writing functions"""

    @patch("pandas.read_csv")
    def test_read_df_from_csv_calls_pandas_read_csv(self, mock_read_csv):
        """Test that read_df_from_csv calls pd.read_csv with correct path"""
        # Arrange
        mock_df = MagicMock()
        mock_read_csv.return_value = mock_df

        # Act
        result = read_df_from_csv("test_file.csv")

        # Assert
        expected_path = f"{settings.DATA_PATH}/test_file.csv"
        mock_read_csv.assert_called_once_with(expected_path, low_memory=False)
        self.assertEqual(result, mock_df)

    @patch("pandas.DataFrame.to_csv")
    def test_write_df_to_csv_calls_dataframe_to_csv(self, _mock_to_csv):
        """Test that write_df_to_csv calls df.to_csv with correct path"""
        # Arrange
        mock_df = MagicMock(spec=pd.DataFrame)

        # Act
        write_df_to_csv(mock_df, "test_output.csv")

        # Assert
        expected_path = f"{settings.DATA_PATH}/test_output.csv"
        mock_df.to_csv.assert_called_once_with(expected_path, index=False)

    @patch("os.path.isfile")
    @patch("scraper.utils.read_df_from_csv")
    @patch("scraper.utils.write_df_to_csv")
    def test_read_write_data_uses_existing_file(self, _mock_write_df, mock_read_df, mock_isfile):
        """Test that read_write_data uses existing file when available"""
        # Arrange
        mock_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        mock_isfile.return_value = True
        mock_read_df.return_value = mock_df
        mock_func = MagicMock()

        # Act
        result = read_write_data("test_data", mock_func, "arg1", kwarg1="value")

        # Assert
        mock_isfile.assert_called_once_with(f"{settings.DATA_PATH}/test_data.csv")
        mock_read_df.assert_called_once_with("test_data.csv")
        mock_func.assert_not_called()  # Function should not be called when file exists
        pd.testing.assert_frame_equal(result, mock_df)

    @patch("os.path.isfile")
    @patch("scraper.utils.read_df_from_csv")
    @patch("scraper.utils.write_df_to_csv")
    def test_read_write_data_generates_new_data(self, mock_write_df, mock_read_df, mock_isfile):
        """Test that read_write_data generates new data when file doesn't exist"""
        # Arrange
        mock_isfile.return_value = False
        mock_read_df.return_value = pd.DataFrame()  # Empty dataframe

        # Function should return a list of dicts that gets converted to DataFrame
        func_result = [{"col1": 10, "col2": 20}, {"col1": 30, "col2": 40}]
        mock_func = MagicMock(return_value=func_result)
        mock_func.__name__ = "mock_func"  # Set the __name__ attribute

        # Act
        read_write_data("test_data", mock_func, "arg1", kwarg1="value")

        # Assert
        mock_isfile.assert_called_once_with(f"{settings.DATA_PATH}/test_data.csv")
        mock_func.assert_called_once_with("arg1", kwarg1="value")

        # Check that the result was written to a file
        expected_df = pd.DataFrame(func_result)
        mock_write_df.assert_called_once()
        # Compare the first argument (DataFrame) of the first call
        called_df = mock_write_df.call_args[0][0]
        pd.testing.assert_frame_equal(called_df, expected_df)

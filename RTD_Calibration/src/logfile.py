import pandas as pd
import os

class Logfile:
    def __init__(self, filepath: str = None, df: pd.DataFrame = None, save_parsed: str = None) -> None:
        """
        Class to handle reading and normalizing a local CSV logfile.

        Parameters:
            filepath (str, optional): Path to the local CSV file. If not provided, `df` must be provided.
            df (pd.DataFrame, optional): Preloaded DataFrame to use directly.
            save_parsed (str, optional): If provided, the normalized dataframe will be written to this path as CSV.
        """
        self.filepath = filepath
        self._raw = df
        self.log_file = self.download_logfile()
        if save_parsed and isinstance(self.log_file, pd.DataFrame):
            try:
                os.makedirs(os.path.dirname(save_parsed), exist_ok=True)
                self.log_file.to_csv(save_parsed, index=False)
                print(f"Parsed logfile saved to: {save_parsed}")
            except Exception as e:
                print(f"Warning: could not save parsed logfile to {save_parsed}: {e}")

    def download_logfile(self):
        """
        Function to read data from a local CSV file.

        Returns:
            pandas.DataFrame: DataFrame containing the data from the CSV file.
        """
        try:
            # If DataFrame supplied, use it
            if isinstance(self._raw, pd.DataFrame):
                df = self._raw.copy()
            else:
                if not self.filepath or not os.path.exists(self.filepath):
                    raise FileNotFoundError(f"Logfile not found at '{self.filepath}'")
                df = pd.read_csv(self.filepath)

            # Normalize column names and common columns
            df = df.rename(columns=lambda c: c.strip())
            # Ensure expected columns exist; add placeholders if needed
            expected = ["Filename", "Selection", "CalibSetNumber", "Date", "N_Run"]
            for col in expected:
                if col not in df.columns:
                    df[col] = None

            # Coerce CalibSetNumber to numeric when possible
            # BUT: preserve string values like "FRAME_SET1", "FRAME_SET2", etc.
            try:
                if "CalibSetNumber" in df.columns:
                    # Check if column contains any "FRAME_SET" strings
                    has_frame_set = df["CalibSetNumber"].astype(str).str.contains('FRAME_SET', case=False, na=False).any()
                    
                    if not has_frame_set:
                        # Only convert to numeric if no FRAME_SET values present
                        df["CalibSetNumber"] = pd.to_numeric(df["CalibSetNumber"], errors='coerce')
                    # Otherwise keep original string/object dtype
            except Exception:
                pass

            print(f"CSV file loaded successfully from '{self.filepath or 'provided DataFrame'}'.")
            return df
        except Exception as e:
            raise RuntimeError(f"An error occurred while reading the log file: {e}")

    def select_files(self, **kwargs): 
        """
        Select files from a log file DataFrame based on given conditions.

        Parameters:
            kwargs (dict): Dictionary of column-value pairs specifying conditions for selection.
                Values can be a single value or a list of values.

        Returns:
            pandas.DataFrame: DataFrame containing selected rows based on the conditions.
        """
        try:
            selection = self.log_file.copy()  # Create a copy of the original DataFrame to avoid direct modification

            for column, value in kwargs.items():
                # Check that the column exists in the DataFrame
                if column not in selection.columns:
                    raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

                # Check if the value is a list (value provided as kwargs argument)
                if isinstance(value, list):
                    # Use isin() to filter rows where the column value is in the list
                    selection = selection.loc[selection[column].isin(value)]
                else:
                    # If the value is not a list, filter rows where the column value matches
                    selection = selection.loc[selection[column] == value]

            return selection

        except Exception as e:
            # In case of error, raise a detailed exception
            raise RuntimeError(f"An error occurred while selecting files: {e}")

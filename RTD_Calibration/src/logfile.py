import pandas as pd
import os

class Logfile:
    def __init__(self, filepath: str = None, df: pd.DataFrame = None, save_parsed: str = None) -> None:
        """
        Class to handle reading and normalizing a local CSV logfile.

        Parameters:
            filepath (str, optional): Path to the local CSV file. If not provided, `df` must be provided.
            df (pd.DataFrame, optional): Preloaded DataFrame to use directly.
            save_parsed (str, optional): If provided, the normalized dataframe will be written to this path as CSV. (save_parsed = 'data/results/parsed_logfile.csv', for example.) 
        """
        self.filepath = filepath
        self._raw = df
        self.log_file = self.download_logfile()
        if save_parsed and isinstance(self.log_file, pd.DataFrame): #se comprueba que la instancia sea un DataFrame de pandas antes de guardar el df normalizado en CSV en disco.
            try:
                os.makedirs(os.path.dirname(save_parsed), exist_ok=True) # Crear directorio si no existe, si ya existe no hace nada.
                self.log_file.to_csv(save_parsed, index=False) # Guardar sin índice de pandas en el CSV.
                print(f"Parsed logfile saved to: {save_parsed}")
            except Exception as e: # Captura cualquier error al guardar el CSV.
                print(f"Warning: could not save parsed logfile to {save_parsed}: {e}")

    def download_logfile(self):
        """
        Function to read data from a local CSV file. If a DataFrame is provided, it uses that directly.

        Returns:
            pandas.DataFrame: DataFrame containing the data from the CSV file. 
        """
        try:
            # If DataFrame supplied, use it
            if isinstance(self._raw, pd.DataFrame): #si es cierto que se ha proporcionado un DataFrame, se usa directamente.
                df = self._raw.copy() # Crear una copia para evitar modificar el original.
            else:
                if not self.filepath or not os.path.exists(self.filepath): #si no se ha proporcionado filepath o no existe el archivo en la ruta dada, se lanza error.
                    raise FileNotFoundError(f"Logfile not found at '{self.filepath}'")
                df = pd.read_csv(self.filepath) # Leer el CSV desde la ruta dada.

            # Normalize column names and common columns:
            df = df.rename(columns=lambda c: c.strip()) # Eliminar espacios en blanco accidentales en los nombres de las columnas con la función lambda c: c.strip().
            # Ensure expected columns exist; add placeholders (None) if needed:
            expected = ["Filename", "Selection", "CalibSetNumber", "Date", "N_Run"]
            for col in expected:
                if col not in df.columns: #si alguna de las columnas esperadas no está en el DataFrame, se añade con valores None.
                    df[col] = None # Añadir columna vacía si no existe.

            # Coerce CalibSetNumber to numeric when possible
            # BUT: preserve string values like "FRAME_SET1", "FRAME_SET2", "RESIST_SET", etc.
            try:
                if "CalibSetNumber" in df.columns: #solo si la columna CalibSetNumber está en el DataFrame.
                    has_special_set = df["CalibSetNumber"].astype(str).str.contains('SET', case=False, na=False).any() # Comprobar si hay valores que contienen 'SET' (FRAME_SET, RESIST_SET, etc.).
                    
                    if not has_special_set:
                        # Only convert to numeric if no special SET tags present
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
                Values can be a single value or a list of values, for example:
                    select_files(Selection='CALIBRATION', CalibSetNumber=[1, 2, 3])
        Returns:
            pandas.DataFrame: DataFrame containing selected rows based on the conditions. 
        """
        try:
            selection = self.log_file.copy()  # Create a copy of the original DataFrame to avoid direct modification

            for column, value in kwargs.items(): # Iterar sobre cada condición proporcionada en kwargs
                if column not in selection.columns: #si la columna dada en kwargs no está en el DataFrame, se lanza error.
                    raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

                if isinstance(value, list): #si el valor de value dado en kwargs es una lista, 
                    selection = selection.loc[selection[column].isin(value)] # Filtrar filas donde el valor de la columna está en la lista.
                else:
                    selection = selection.loc[selection[column] == value] # Si el valor no es una lista, filtrar filas donde el valor de la columna coincide exactamente.

            return selection

        except Exception as e:
            # In case of error, raise a detailed exception
            raise RuntimeError(f"An error occurred while selecting files: {e}")

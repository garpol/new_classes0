import pandas as pd
import os

class Logfile:
    def __init__(self, filepath: str = None, df: pd.DataFrame = None, save_parsed: str = None) -> None:
        """
        Clase para leer y normalizar un archivo CSV de log local.

        Parámetros:
            filepath (str, opcional): Ruta al archivo CSV local. Si no se proporciona, se debe dar 'df'.
            df (pd.DataFrame, opcional): DataFrame ya cargado para usar directamente.
            save_parsed (str, opcional): Si se proporciona, el DataFrame normalizado se guardará en esta ruta como CSV.
                                         Ejemplo: save_parsed = 'data/results/parsed_logfile.csv'
        """
        self.filepath = filepath
        self._raw = df
        self.log_file = self.download_logfile()
        # Si se especificó ruta para guardar, guardar el DataFrame normalizado
        if save_parsed and isinstance(self.log_file, pd.DataFrame):
            try:
                # Crear directorio si no existe
                os.makedirs(os.path.dirname(save_parsed), exist_ok=True)
                # Guardar CSV sin índice de pandas
                self.log_file.to_csv(save_parsed, index=False)
                print(f"Parsed logfile saved to: {save_parsed}")
            except Exception as e:
                print(f"Warning: could not save parsed logfile to {save_parsed}: {e}")

    def download_logfile(self):
        """
        Lee datos desde un archivo CSV local. Si se proporcionó un DataFrame, lo usa directamente.

        Returns:
            pandas.DataFrame: DataFrame con los datos del archivo CSV.
        """
        try:
            # Si se proporcionó un DataFrame, usarlo directamente
            if isinstance(self._raw, pd.DataFrame):
                df = self._raw.copy()  # Crear copia para evitar modificar el original
            else:
                # Verificar que exista el archivo
                if not self.filepath or not os.path.exists(self.filepath):
                    raise FileNotFoundError(f"Logfile not found at '{self.filepath}'")
                df = pd.read_csv(self.filepath)

            # Normalizar nombres de columnas eliminando espacios en blanco
            df = df.rename(columns=lambda c: c.strip())
            
            # Asegurar que existan las columnas esperadas, añadir con None si faltan
            expected = ["Filename", "Selection", "CalibSetNumber", "Date", "N_Run"]
            for col in expected:
                if col not in df.columns:
                    df[col] = None  # Añadir columna vacía si no existe

            # Convertir CalibSetNumber a numérico cuando sea posible
            # PERO: preservar valores string como "FRAME_SET1", "RESIST_SET", etc.
            try:
                if "CalibSetNumber" in df.columns:
                    # Comprobar si hay valores especiales que contienen 'SET' (FRAME_SET, RESIST_SET, etc.)
                    has_special_set = df["CalibSetNumber"].astype(str).str.contains('SET', case=False, na=False).any()
                    
                    if not has_special_set:
                        # Solo convertir a numérico si no hay etiquetas SET especiales
                        df["CalibSetNumber"] = pd.to_numeric(df["CalibSetNumber"], errors='coerce')
                    # Si hay valores especiales, mantener el tipo string/object original
            except Exception:
                pass

            print(f"CSV file loaded successfully from '{self.filepath or 'provided DataFrame'}'.")
            return df
        except Exception as e:
            raise RuntimeError(f"An error occurred while reading the log file: {e}")

    def select_files(self, **kwargs): 
        """
        Selecciona archivos del DataFrame de log basado en condiciones dadas.

        Parámetros:
            kwargs (dict): Diccionario de pares columna-valor especificando condiciones de selección.
                Los valores pueden ser un valor único o una lista de valores, por ejemplo:
                    select_files(Selection='CALIBRATION', CalibSetNumber=[1, 2, 3])
        
        Returns:
            pandas.DataFrame: DataFrame con las filas seleccionadas según las condiciones.
        """
        try:
            selection = self.log_file.copy()  # Crear copia para evitar modificar el original

            # Iterar sobre cada condición proporcionada
            for column, value in kwargs.items():
                # Verificar que la columna exista
                if column not in selection.columns:
                    raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

                # Si el valor es una lista, usar .isin()
                if isinstance(value, list):
                    selection = selection.loc[selection[column].isin(value)]
                # Si es un valor único, filtrar por igualdad exacta
                else:
                    selection = selection.loc[selection[column] == value]

            return selection

        except Exception as e:
            raise RuntimeError(f"An error occurred while selecting files: {e}")

"""
Clase Run simplificada - Procesa un archivo de calibración individual.

Responsabilidades:
- Cargar archivo de temperaturas
- Limpiar datos inválidos
- Asociar sensores a canales
- Calcular offsets entre sensores
"""
import glob
from pathlib import Path
import numpy as np
import pandas as pd
import yaml


class Run:
    """Procesa un archivo de calibración individual."""
    
    def __init__(self, filename: str, logfile: pd.DataFrame, config: dict = None) -> None:
        """
        Crea una instancia de Run.
        
        Args:
            filename: Nombre del archivo de temperaturas (sin .txt)
            logfile: DataFrame con información de mapeo de sensores
            config: Diccionario con configuración (opcional, se carga de config.yml)
        """
        self.filename = filename
        self.logfile = logfile
        self.temperature_data = None
        self.sensor_mapping = None
        self.defective_channels = []
        
        # Cargar configuración
        if config is None:
            config = self._load_config()
        self.config = config
        
        # Obtener parámetros de run_options
        run_opts = self.config.get('run_options', {})
        self.max_nan_threshold = run_opts.get('max_nan_threshold', 40)
        temp_range = run_opts.get('valid_temp_range', {})
        self.temp_min = temp_range.get('min', 60)
        self.temp_max = temp_range.get('max', 350)
        
        # Cargar automáticamente
        self._load_and_process()
    
    def _load_config(self):
        """Carga el archivo de configuración."""
        repo_root = Path(__file__).parents[1]
        config_path = repo_root / "config" / "config.yml"
        
        if not config_path.exists():
            print(f"Advertencia: No se encontró {config_path}, usando valores por defecto")
            return {}
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_and_process(self):
        """Carga y procesa el archivo de temperaturas."""
        try:
            self._load_temperature_file()
            self._associate_sensors()
        except Exception as e:
            print(f"Error procesando {self.filename}: {e}")
            self.temperature_data = pd.DataFrame()
    
    def _load_temperature_file(self):
        """Busca y carga el archivo de temperaturas."""
        # Buscar archivo
        repo_root = Path(__file__).parents[1]
        search_path = repo_root / "data" / "temperature_files"
        
        matches = glob.glob(str(search_path / "**" / f"{self.filename}.txt"), recursive=True)
        if not matches:
            raise FileNotFoundError(f"No se encontró {self.filename}.txt")
        
        filepath = matches[0]
        print(f"Cargando: {filepath}")
        
        # Leer archivo (sin encabezado, separado por tabulaciones)
        df = pd.read_csv(filepath, sep="\t", header=None)
        
        # Nombrar columnas
        cols = ["Date", "Time"] + [f"channel_{i}" for i in range(1, 15)]
        df.columns = cols + list(df.columns[len(cols):])
        
        # Parsear fechas
        df["datetime"] = pd.to_datetime(
            df["Date"] + " " + df["Time"], 
            errors="coerce",
            format="%m/%d/%Y %I:%M:%S %p"
        )
        if df["datetime"].isna().all():
            df["datetime"] = pd.to_datetime(
                df["Date"] + " " + df["Time"], 
                errors="coerce"
            )
        
        # Extraer solo canales de temperatura
        temp_cols = [c for c in df.columns if c.startswith("channel_")]
        temps = df[temp_cols].copy()
        temps.index = df["datetime"]
        
        # Filtrar valores inválidos (rango configurable desde config.yml)
        temps = temps.mask((temps < self.temp_min) | (temps > self.temp_max))
        temps = temps.dropna(how="all")
        
        # Detectar canales defectuosos (umbral configurable desde config.yml)
        nan_counts = temps.isna().sum()
        self.defective_channels = nan_counts[nan_counts > self.max_nan_threshold].index.tolist()
        if self.defective_channels:
            print(f"  Canales defectuosos: {self.defective_channels}")
        
        self.temperature_data = temps
        print(f"  Datos cargados: {len(temps)} registros")
    
    def _associate_sensors(self):
        """Asocia sensores RTD a los canales de temperatura."""
        if self.temperature_data is None or self.temperature_data.empty:
            return
        
        # Buscar filename en logfile
        match = self.logfile[self.logfile["Filename"] == self.filename]
        if match.empty:
            raise ValueError(f"No se encontró {self.filename} en el logfile")
        
        # Extraer IDs de sensores (S1 a S20)
        sensor_cols = [f"S{i}" for i in range(1, 21)]
        sensor_ids = match[sensor_cols].iloc[0].dropna().values
        
        # Convertir a strings de enteros
        sensor_ids = [str(int(float(x))) for x in sensor_ids if pd.notna(x)]
        
        # Mapear channel_1..channel_14 a sensor IDs
        channels = [f"channel_{i}" for i in range(1, 15)]
        self.sensor_mapping = dict(zip(channels, sensor_ids[:14]))
        
        # Renombrar columnas en temperature_data
        self.temperature_data = self.temperature_data.rename(columns=self.sensor_mapping)
        print(f"  Sensores asociados: {len(self.sensor_mapping)}")
    
    def calculate_offsets(self, time_start=20, time_end=40):
        """
        Calcula offsets entre sensores en una ventana de tiempo.
        
        Args:
            time_start: Inicio de ventana en minutos desde el comienzo
            time_end: Fin de ventana en minutos desde el comienzo
            
        Returns:
            DataFrame con offsets (sensor_i - sensor_j)
        """
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No hay datos de temperatura")
        
        # Seleccionar ventana de tiempo
        t0 = self.temperature_data.index.min() + pd.Timedelta(minutes=time_start)
        t1 = self.temperature_data.index.min() + pd.Timedelta(minutes=time_end)
        window = self.temperature_data.loc[t0:t1]
        
        if window.empty:
            raise ValueError("Ventana de tiempo vacía")
        
        # Calcular offsets entre todos los pares de sensores
        sensors = list(window.columns)
        offsets = pd.DataFrame(0.0, index=sensors, columns=sensors)
        
        for i, s1 in enumerate(sensors):
            for j, s2 in enumerate(sensors):
                if i == j:
                    offsets.loc[s1, s2] = 0.0
                elif i < j:
                    diff = (window[s1] - window[s2]).mean()
                    offsets.loc[s1, s2] = diff
                    offsets.loc[s2, s1] = -diff
        
        return offsets
    
    def calculate_offset_errors(self, time_start=-20, time_end=0):
        """
        Calcula errores RMS de offsets en una ventana (por defecto últimos 20 min).
        
        Args:
            time_start: Inicio relativo al final (negativo = antes del final)
            time_end: Fin relativo al final
            
        Returns:
            DataFrame con errores RMS
        """
        if self.temperature_data is None or self.temperature_data.empty:
            raise ValueError("No hay datos de temperatura")
        
        # Ventana desde el final
        t_end = self.temperature_data.index.max()
        t0 = t_end + pd.Timedelta(minutes=time_start)
        t1 = t_end + pd.Timedelta(minutes=time_end)
        window = self.temperature_data.loc[t0:t1]
        
        # Calcular offsets primero
        offsets_ref = self.calculate_offsets()
        
        # Calcular RMS de las diferencias respecto al offset medio
        sensors = list(window.columns)
        errors = pd.DataFrame(0.0, index=sensors, columns=sensors)
        
        for i, s1 in enumerate(sensors):
            for j, s2 in enumerate(sensors):
                if i == j:
                    errors.loc[s1, s2] = 0.0
                elif i < j:
                    mean_offset = offsets_ref.loc[s1, s2]
                    diff = window[s1] - window[s2]
                    rms = np.sqrt(((diff - mean_offset) ** 2).mean())
                    errors.loc[s1, s2] = rms
                    errors.loc[s2, s1] = rms
        
        return errors

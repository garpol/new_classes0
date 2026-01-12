"""
Clase Sensor - Representación OOP de un sensor RTD individual

NOTA: Esta clase es un diseño provisional/experimental para futura refactorización.
      Actualmente NO SE USA en el código (run.py sigue usando dicts y DataFrames).
      
=============================================================================
EJEMPLO DE USO FUTURO (activación en run.py):
=============================================================================

# 1. Importar en run.py
from .sensor import Sensor, create_sensors_from_mapping

# 2. Modificar _associate_sensors() en Run
def _associate_sensors(self):
    # ... código actual (mapeo de channels) ...
    self.sensor_mapping = dict(zip(channels, sensor_ids[:14]))
    self.temperature_data = self.temperature_data.rename(columns=self.sensor_mapping)
    
    # NUEVO: Crear objetos Sensor
    self.sensors = create_sensors_from_mapping(
        sensor_mapping=self.sensor_mapping,
        temperature_data=self.temperature_data,
        config=self.config  # Pasar config para validaciones
    )
    
    # Enriquecer con metadata del logfile (opcional)
    for sensor in self.sensors:
        sensor.enrich_from_metadata(self.metadata)
    
    print(f"  Sensores asociados: {len(self.sensors)}")

# 3. Usar en calculate_offsets() (opcional, o seguir usando DataFrame)
def calculate_offsets_oop(self, time_start=20, time_end=40):
    '''Versión OOP usando objetos Sensor.'''
    offsets = {}
    errors = {}
    
    for s1 in self.sensors:
        for s2 in self.sensors:
            if s1.id != s2.id:
                offset, error = s1.offset_to(s2, time_start, time_end)
                offsets[(s1.id, s2.id)] = offset
                errors[(s1.id, s2.id)] = error
    
    return offsets, errors

# 4. Filtrar sensores defectuosos
defective = [s for s in run.sensors if s.is_defective()]
good_sensors = [s for s in run.sensors if not s.is_defective()]

# 5. Acceder a metadata de cada sensor
for sensor in run.sensors:
    print(f"{sensor.id}: Set {sensor.set_number}, Ref={sensor.is_reference}")

# 6. Visualización individual
sensor = run.sensors[0]
sensor.plot()  # Gráfico automático

=============================================================================
Ventajas de usar esta clase:
- Encapsulación: cada sensor tiene su comportamiento
- Validación: is_defective(), is_stable(), etc.
- Metadata: calibration_date, batch_number, set_number, etc.
- Interfaz limpia: sensor.temperatures, sensor.mean_temp
- Extensible: añadir métodos sin modificar run.py/set.py/tree.py
=============================================================================
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, Any


class Sensor:
    """
    Representa un sensor RTD individual con sus datos y comportamiento.
    
    Esta clase NO duplica datos - mantiene una referencia al DataFrame
    completo y accede a sus datos mediante propiedades.
    """
    
    def __init__(self, sensor_id: int, channel: str, data: pd.DataFrame, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Crea una instancia de Sensor.
        
        Args:
            sensor_id: ID numérico del sensor RTD (ej: 48178)
            channel: Nombre del canal de adquisición (ej: 'channel_1')
            data: DataFrame completo con todas las temperaturas (referencia)
                  Las columnas deben ser los IDs de sensores (como strings)
            config: Diccionario de configuración (opcional, para validaciones)
        
        Examples:
            >>> temps = pd.DataFrame({'48178': [76.5, 76.6], '48179': [76.4, 76.5]})
            >>> sensor = Sensor(48178, 'channel_1', temps)
            >>> sensor.id
            48178
        """
        self.id = sensor_id
        self.channel = channel
        self._data = data  # Referencia al DataFrame (no copia)
        self._config = config or {}
        
        # Metadata del logfile (se enriquece con enrich_from_metadata())
        self.set_number = None  # Número del set de calibración
        self.is_reference = False  # Si es sensor de referencia
        self.run_date = None  # Fecha del experimento
        self.liquid_media = None  # LN2, etc.
        self.board = None  # Placa de adquisición
        
        # Resultados de calibración (se calculan en Set/Tree)
        self.calibration_constant = None  # Constante de calibración final
        self.calibration_error = None  # Error asociado
        self.calibration_paths = []  # Caminos usados en Tree
        
        # Estado del sensor
        self.defective = False
        self._defective_reason = None  # "Too many NaNs", "Unstable", etc.
        
    @property
    def temperatures(self) -> pd.Series:
        """
        Obtiene la serie temporal de temperatura de este sensor.
        
        Returns:
            pd.Series: Serie con index temporal y valores de temperatura
        
        Examples:
            >>> sensor.temperatures.head()
            2022-01-02 13:05:31    76.514
            2022-01-02 13:05:32    76.515
            dtype: float64
        """
        return self._data[str(self.id)]
    
    def enrich_from_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Enriquece el sensor con metadata del run (desde logfile).
        
        Llamar después de crear el sensor para añadir información contextual.
        
        Args:
            metadata: Diccionario con metadata del run (de get_run_metadata())
        
        Examples:
            >>> sensor.enrich_from_metadata(run.metadata)
            >>> print(sensor.set_number)
            1
            >>> print(sensor.is_reference)
            True
        
        Notes:
            - Se llama automáticamente en run._associate_sensors() (futuro)
            - Verifica si el sensor es referencia comparando con ref1_id/ref2_id
        """
        if not metadata:
            return
        
        self.set_number = metadata.get('set_number')
        self.run_date = metadata.get('date')
        self.liquid_media = metadata.get('liquid_media')
        self.board = metadata.get('board')
        
        # Detectar si es sensor de referencia
        ref1_id = metadata.get('ref1_id')
        ref2_id = metadata.get('ref2_id')
        if self.id in [ref1_id, ref2_id]:
            self.is_reference = True
    
    def update_calibration(self, constant: float, error: float, 
                          paths: Optional[list] = None) -> None:
        """
        Actualiza los resultados de calibración del sensor.
        
        Se llama desde Set.py o Tree.py después de calcular constantes.
        
        Args:
            constant: Constante de calibración calculada
            error: Error asociado a la constante
            paths: Lista de caminos usados en Tree (opcional)
        
        Examples:
            >>> sensor.update_calibration(1.0234, 0.0012, paths=['48176->48178'])
            >>> print(f"{sensor.calibration_constant:.4f} ± {sensor.calibration_error:.4f}")
            1.0234 ± 0.0012
        """
        self.calibration_constant = constant
        self.calibration_error = error
        if paths:
            self.calibration_paths = paths
    
    @property
    def mean_temp(self) -> float:
        """Temperatura media del sensor en todo el run."""
        return self.temperatures.mean()
    
    @property
    def std_temp(self) -> float:
        """Desviación estándar de temperatura en todo el run."""
        return self.temperatures.std()
    
    @property
    def min_temp(self) -> float:
        """Temperatura mínima registrada."""
        return self.temperatures.min()
    
    @property
    def max_temp(self) -> float:
        """Temperatura máxima registrada."""
        return self.temperatures.max()
    
    @property
    def nan_count(self) -> int:
        """Número de valores NaN en la serie temporal."""
        return self.temperatures.isna().sum()
    
    def get_window(self, time_start: int, time_end: int) -> pd.Series:
        """
        Extrae una ventana temporal de las temperaturas.
        
        Args:
            time_start: Minuto de inicio desde el comienzo del run
            time_end: Minuto final
        
        Returns:
            pd.Series: Subconjunto de temperaturas en la ventana
        
        Examples:
            >>> window = sensor.get_window(20, 40)  # Minutos 20-40
            >>> window.mean()
            76.623
        """
        start_time = self.temperatures.index.min() + pd.Timedelta(minutes=time_start)
        end_time = self.temperatures.index.min() + pd.Timedelta(minutes=time_end)
        return self.temperatures[start_time:end_time]
    
    def is_stable(self, time_start: int = 20, time_end: int = 40, 
                  threshold: float = 0.1) -> bool:
        """
        Verifica si el sensor está estable en una ventana temporal.
        
        Un sensor se considera estable si su desviación estándar
        en la ventana es menor que el threshold.
        
        Args:
            time_start: Inicio de ventana en minutos
            time_end: Fin de ventana en minutos
            threshold: Threshold de estabilidad en Kelvin (default: 0.1K)
        
        Returns:
            bool: True si está estable, False en caso contrario
        
        Examples:
            >>> sensor.is_stable(20, 40, threshold=0.1)
            True
        """
        window = self.get_window(time_start, time_end)
        if window.empty:
            return False
        return window.std() < threshold
    
    def is_defective(self, max_nan_threshold: Optional[int] = None) -> bool:
        """
        Verifica si el sensor es defectuoso por exceso de NaNs.
        
        Args:
            max_nan_threshold: Máximo número de NaNs permitidos.
                              Si None, usa el valor de config (default: 40)
        
        Returns:
            bool: True si es defectuoso, False si funciona bien
        
        Examples:
            >>> sensor.is_defective()
            False
            >>> sensor.is_defective(max_nan_threshold=10)
            True
        """
        # Obtener threshold desde config o usar default
        if max_nan_threshold is None:
            run_opts = self._config.get('run_options', {})
            max_nan_threshold = run_opts.get('max_nan_threshold', 40)
        
        # Asegurar que no es None para type checker
        threshold = max_nan_threshold if max_nan_threshold is not None else 40
        is_def = self.nan_count > threshold
        
        if is_def:
            self.defective = True
            self._defective_reason = f"Too many NaNs ({self.nan_count} > {threshold})"
        
        return is_def
    
    def offset_to(self, other: 'Sensor', time_start: int = 20, 
                  time_end: int = 40) -> Tuple[float, float]:
        """
        Calcula el offset y error respecto a otro sensor.
        
        Args:
            other: Otro objeto Sensor para comparar
            time_start: Inicio de ventana en minutos
            time_end: Fin de ventana en minutos
        
        Returns:
            tuple: (offset, error_rms)
                - offset: Diferencia media de temperatura
                - error_rms: Error RMS de la medición
        
        Examples:
            >>> offset, error = sensor1.offset_to(sensor2, 20, 40)
            >>> print(f"{offset:.3f} ± {error:.3f} K")
            0.023 ± 0.002 K
        
        Notes:
            - offset > 0: este sensor lee más alto que 'other'
            - offset < 0: este sensor lee más bajo que 'other'
        """
        # Obtener ventanas temporales
        window_self = self.get_window(time_start, time_end)
        window_other = other.get_window(time_start, time_end)
        
        # Calcular diferencia temporal
        diff = window_self - window_other
        
        # Offset = media de las diferencias
        offset = diff.mean()
        
        # Error RMS = sqrt(mean((diff - offset)^2))
        rms_error = np.sqrt(((diff - offset) ** 2).mean())
        
        return offset, rms_error
    
    def plot(self, ax=None, **kwargs):
        """
        Plotea la serie temporal del sensor.
        
        Args:
            ax: Matplotlib axis (opcional, crea uno nuevo si es None)
            **kwargs: Argumentos adicionales para plot()
        
        Returns:
            matplotlib axis con el gráfico
        
        Examples:
            >>> import matplotlib.pyplot as plt
            >>> fig, ax = plt.subplots()
            >>> sensor.plot(ax=ax, label=f'Sensor {sensor.id}')
            >>> plt.show()
        """
        import matplotlib.pyplot as plt
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        self.temperatures.plot(ax=ax, **kwargs)
        ax.set_xlabel('Tiempo')
        ax.set_ylabel('Temperatura (K)')
        ax.set_title(f'Sensor {self.id} (Canal {self.channel})')
        ax.grid(True, alpha=0.3)
        
        return ax
    
    def summary(self) -> dict:
        """
        Genera un resumen estadístico del sensor.
        
        Returns:
            dict: Diccionario con estadísticas y metadata del sensor
        
        Examples:
            >>> summary = sensor.summary()
            >>> print(summary['mean'])
            76.623
            >>> print(summary['set_number'])
            1
        """
        return {
            # Identificación
            'id': self.id,
            'channel': self.channel,
            
            # Estadísticas de temperatura
            'mean': self.mean_temp,
            'std': self.std_temp,
            'min': self.min_temp,
            'max': self.max_temp,
            'nan_count': self.nan_count,
            
            # Estado
            'is_defective': self.is_defective(),
            'defective_reason': self._defective_reason,
            'is_stable': self.is_stable(),
            
            # Metadata del run
            'set_number': self.set_number,
            'is_reference': self.is_reference,
            'run_date': self.run_date,
            'liquid_media': self.liquid_media,
            'board': self.board,
            
            # Calibración (si existe)
            'calibration_constant': self.calibration_constant,
            'calibration_error': self.calibration_error,
            'calibration_paths': self.calibration_paths,
        }
    
    def __repr__(self) -> str:
        """Representación string del sensor."""
        status = "DEFECTIVE" if self.defective else "OK"
        ref = " [REF]" if self.is_reference else ""
        return f"Sensor(id={self.id}, channel={self.channel}, status={status}{ref})"
    
    def __str__(self) -> str:
        """String legible para el usuario."""
        ref = " [REFERENCIA]" if self.is_reference else ""
        set_info = f" Set{self.set_number}" if self.set_number else ""
        return f"Sensor {self.id}{ref}{set_info} [{self.channel}]: {self.mean_temp:.2f}K ± {self.std_temp:.3f}K"
    
    def __eq__(self, other) -> bool:
        """Igualdad basada en el ID del sensor."""
        if not isinstance(other, Sensor):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash basado en el ID (permite usar en sets y dicts)."""
        return hash(self.id)


# ============================================================================
# FUNCIONES HELPER PARA TRABAJAR CON COLECCIONES DE SENSORES
# ============================================================================

def create_sensors_from_mapping(sensor_mapping: dict, 
                                 temperature_data: pd.DataFrame,
                                 config: Optional[Dict[str, Any]] = None) -> list:
    """
    Crea una lista de objetos Sensor desde un sensor_mapping.
    
    Función helper para migrar desde el código actual (dicts) a clases.
    
    Args:
        sensor_mapping: Dict con formato {'channel_1': '48178', ...}
        temperature_data: DataFrame con temperaturas
        config: Diccionario de configuración (opcional)
    
    Returns:
        list: Lista de objetos Sensor
    
    Examples:
        >>> mapping = {'channel_1': '48178', 'channel_2': '48179'}
        >>> sensors = create_sensors_from_mapping(mapping, temps_df, config)
        >>> len(sensors)
        2
    
    Notes:
        Esta es la función de migración que se usaría en run._associate_sensors()
    """
    sensors = []
    for channel, sensor_id in sensor_mapping.items():
        sensor = Sensor(int(sensor_id), channel, temperature_data, config)
        sensors.append(sensor)
    return sensors


def find_sensor_by_id(sensors: list, sensor_id: int) -> Optional[Sensor]:
    """
    Busca un sensor por su ID en una lista.
    
    Args:
        sensors: Lista de objetos Sensor
        sensor_id: ID a buscar
    
    Returns:
        Sensor object o None si no se encuentra
    
    Examples:
        >>> sensor = find_sensor_by_id(sensors, 48178)
        >>> print(sensor.id)
        48178
    """
    for sensor in sensors:
        if sensor.id == sensor_id:
            return sensor
    return None


def get_reference_sensors(sensors: list) -> list:
    """
    Filtra sensores marcados como referencia.
    
    Args:
        sensors: Lista de objetos Sensor
    
    Returns:
        list: Lista de sensores con is_reference=True
    
    Examples:
        >>> refs = get_reference_sensors(sensors)
        >>> [s.id for s in refs]
        [48176, 48177]
    """
    return [s for s in sensors if s.is_reference]


def get_defective_sensors(sensors: list, max_nan_threshold: Optional[int] = None) -> list:
    """
    Filtra sensores defectuosos.
    
    Args:
        sensors: Lista de objetos Sensor
        max_nan_threshold: Threshold de NaNs (usa config si es None)
    
    Returns:
        list: Lista de sensores defectuosos
    
    Examples:
        >>> defective = get_defective_sensors(sensors)
        >>> [s.id for s in defective]
        [48185]
        >>> # Ver razones de fallo
        >>> for s in defective:
        ...     print(f"{s.id}: {s._defective_reason}")
    """
    return [s for s in sensors if s.is_defective(max_nan_threshold)]


# ============================================================================
# EJEMPLO DE INTEGRACIÓN FUTURA CON RUN/SET/TREE
# ============================================================================

"""
EJEMPLO 1: Integración con Run (futuro)
----------------------------------------
# En run.py, método _associate_sensors():

from .sensor import create_sensors_from_mapping

def _associate_sensors(self):
    # ... código actual de mapeo ...
    self.sensor_mapping = dict(zip(channels, sensor_ids[:14]))
    self.temperature_data = self.temperature_data.rename(columns=self.sensor_mapping)
    
    # NUEVO: Crear objetos Sensor
    self.sensors = create_sensors_from_mapping(
        self.sensor_mapping, 
        self.temperature_data,
        self.config
    )
    
    # Enriquecer con metadata del logfile
    for sensor in self.sensors:
        sensor.enrich_from_metadata(self.metadata)
    
    print(f"  Sensores asociados: {len(self.sensors)}")
    print(f"  Referencias: {[s.id for s in self.sensors if s.is_reference]}")


EJEMPLO 2: Uso en Set (futuro)
--------------------------------
# En set.py, después de procesar runs:

class Set:
    def __init__(self, set_id):
        self.runs = [...]  # Lista de objetos Run
        self.sensors = self._collect_all_sensors()
    
    def _collect_all_sensors(self):
        '''Recolecta todos los sensores únicos de todos los runs.'''
        all_sensors = {}
        for run in self.runs:
            for sensor in run.sensors:
                if sensor.id not in all_sensors:
                    all_sensors[sensor.id] = sensor
        return list(all_sensors.values())
    
    def calculate_set_calibrations(self):
        '''Calcula constantes promediando todos los runs del set.'''
        for sensor in self.sensors:
            if not sensor.is_reference:
                # Calcular constante promediando runs
                constants = [...]  # Lógica actual
                mean_const = np.mean(constants)
                error = np.std(constants)
                sensor.update_calibration(mean_const, error)


EJEMPLO 3: Uso en Tree (futuro)
---------------------------------
# En tree.py, propagación de constantes:

class Tree:
    def __init__(self, sets):
        self.sensors = self._collect_all_sensors(sets)
        self.reference_sensors = [s for s in self.sensors if s.is_reference]
    
    def propagate_calibrations(self):
        '''Propaga constantes usando múltiples caminos.'''
        for sensor in self.sensors:
            if sensor.id not in self.reference_sensors:
                paths = self._find_paths(sensor)
                constant, error = self._calculate_from_paths(paths)
                sensor.update_calibration(constant, error, paths)
        
        # Exportar resultados
        self.export_sensor_summary()
    
    def export_sensor_summary(self):
        '''Exporta resumen de todos los sensores.'''
        summaries = [s.summary() for s in self.sensors]
        df = pd.DataFrame(summaries)
        df.to_csv('sensor_calibrations.csv', index=False)


EJEMPLO 4: Análisis y filtrado (futuro)
-----------------------------------------
# Scripts de análisis:

# Filtrar sensores buenos para análisis
good_sensors = [s for s in tree.sensors if not s.is_defective()]

# Agrupar por set
from collections import defaultdict
by_set = defaultdict(list)
for sensor in tree.sensors:
    by_set[sensor.set_number].append(sensor)

# Análisis de estabilidad
unstable = [s for s in tree.sensors if not s.is_stable()]
print(f"Sensores inestables: {[s.id for s in unstable]}")

# Comparar referencias vs calibrados
refs = [s for s in tree.sensors if s.is_reference]
calibrated = [s for s in tree.sensors if s.calibration_constant is not None]

# Exportar solo sensores con problemas
defective = get_defective_sensors(tree.sensors)
for s in defective:
    print(f"{s.id}: {s._defective_reason}")
"""

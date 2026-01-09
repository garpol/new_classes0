"""
Clase Set simplificada - Agrupa múltiples runs del mismo set de calibración.

Responsabilidades:
- Agrupar runs por CalibSetNumber
- Calcular constantes de calibración promediando offsets de todos los runs
- Calcular errores asociados
"""
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
try:
    from .run import Run
    from .logfile import Logfile
except ImportError:
    from run import Run
    from logfile import Logfile


class Set:
    """Agrupa y procesa múltiples runs de calibración."""
    
    def __init__(self, logfile_path: str = None, logfile_df: pd.DataFrame = None, config_path: str = None):
        """
        Crea una instancia de Set.
        
        Args:
            logfile_path: Ruta al archivo LogFile.csv
            logfile_df: DataFrame del logfile (alternativo a logfile_path)
            config_path: Ruta al archivo de configuración YAML
        """
        # Cargar logfile
        if logfile_df is not None:
            self.logfile = logfile_df
        elif logfile_path:
            lf = Logfile(filepath=logfile_path)
            self.logfile = lf.log_file
        else:
            # Ruta por defecto
            repo_root = Path(__file__).parents[1]
            default_path = repo_root / "data" / "LogFile.csv"
            lf = Logfile(filepath=str(default_path))
            self.logfile = lf.log_file
        
        # Cargar configuración
        self.config = self._load_config(config_path)
        
        # Diccionario para almacenar runs agrupados por set
        self.runs_by_set = {}
        
        # Resultados de calibración
        self.calibration_constants = {}
        self.calibration_errors = {}
    
    def _load_config(self, config_path):
        """Carga la configuración desde un archivo YAML."""
        if config_path is None:
            repo_root = Path(__file__).parents[1]
            config_path = repo_root / "config" / "config.yml"
        
        if not Path(config_path).exists():
            print(f"Advertencia: No se encontró config en {config_path}")
            return {}
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def group_runs(self, selected_sets=None):
        """
        Agrupa los runs por CalibSetNumber.
        
        Args:
            selected_sets: Lista de sets a procesar (None = todos)
        """
        print("\n=== Agrupando runs por CalibSetNumber ===")
        
        # Convertir CalibSetNumber a numérico
        self.logfile["CalibSetNumber"] = pd.to_numeric(
            self.logfile["CalibSetNumber"], 
            errors='coerce'
        )
        
        # Obtener sets únicos (solo números enteros positivos)
        all_sets = self.logfile["CalibSetNumber"].dropna().unique()
        all_sets = [s for s in all_sets if s > 0 and s == int(s) and len(str(int(s))) <= 2]
        all_sets = sorted(all_sets)
        
        # Filtrar por selected_sets si se especifica
        if selected_sets:
            all_sets = [s for s in all_sets if s in selected_sets]
        
        print(f"Sets a procesar: {all_sets}")
        
        # Palabras clave a excluir en filenames
        exclude_keywords = ['pre', 'st', 'lar']
        
        for set_num in all_sets:
            print(f"\nProcesando Set {set_num}")
            runs_in_set = self.logfile[self.logfile["CalibSetNumber"] == set_num]
            
            valid_runs = {}
            for _, row in runs_in_set.iterrows():
                filename = row["Filename"]
                selection = row["Selection"]
                
                # Filtrar por palabras clave y selección BAD
                if not isinstance(filename, str):
                    continue
                if any(kw in filename.lower() for kw in exclude_keywords):
                    print(f"  Excluido (keywords): {filename}")
                    continue
                if selection == "BAD":
                    print(f"  Excluido (BAD): {filename}")
                    continue
                
                # Crear instancia de Run con configuración
                try:
                    run = Run(filename, self.logfile, config=self.config)
                    valid_runs[filename] = run
                    print(f"  Incluido: {filename}")
                except Exception as e:
                    print(f"  Error en {filename}: {e}")
            
            if valid_runs:
                self.runs_by_set[set_num] = valid_runs
                print(f"  Total runs válidos: {len(valid_runs)}")
        
        print(f"\nTotal sets procesados: {len(self.runs_by_set)}")
    
    def calculate_calibration_constants(self, selected_sets=None):
        """
        Calcula constantes de calibración para cada set.
        
        Las constantes son el promedio ponderado de los offsets de todos los runs.
        Los errores son la desviación estándar de los offsets entre runs.
        
        Args:
            selected_sets: Lista de sets a procesar (None = todos)
        """
        print("\n=== Calculando constantes de calibración ===")
        
        sets_to_process = selected_sets if selected_sets else list(self.runs_by_set.keys())
        
        for set_num in sets_to_process:
            if set_num not in self.runs_by_set:
                print(f"Advertencia: Set {set_num} no tiene runs cargados")
                continue
            
            print(f"\nSet {set_num}:")
            runs = self.runs_by_set[set_num]
            
            # Recolectar offsets y errores de todos los runs
            offsets_list = []
            errors_list = []
            
            for filename, run in runs.items():
                try:
                    offsets = run.calculate_offsets()
                    errors = run.calculate_offset_errors()
                    offsets_list.append(offsets.values)
                    errors_list.append(errors.values)
                    print(f"  ✓ {filename}")
                except Exception as e:
                    print(f"  ✗ Error en {filename}: {e}")
            
            if not offsets_list:
                print(f"  Sin offsets válidos para set {set_num}")
                continue
            
            # Convertir a arrays
            offsets_array = np.array(offsets_list)  # shape: (n_runs, n_sensors, n_sensors)
            errors_array = np.array(errors_list)
            
            # Calcular promedio ponderado por inverso del error al cuadrado
            # Donde error = 0 o NaN, usar peso = 0
            weights = np.zeros_like(errors_array)
            mask_valid = (errors_array > 0) & np.isfinite(errors_array) & np.isfinite(offsets_array)
            weights[mask_valid] = 1.0 / (errors_array[mask_valid] ** 2)
            
            # Promedio ponderado
            weighted_sum = np.sum(offsets_array * weights, axis=0)
            total_weights = np.sum(weights, axis=0)
            
            # Evitar división por cero
            constants = np.divide(
                weighted_sum, 
                total_weights, 
                out=np.full_like(weighted_sum, np.nan),
                where=total_weights > 0
            )
            
            # Error = desviación estándar de los offsets
            errors = np.std(offsets_array, axis=0, ddof=1)
            
            # Convertir a DataFrames con nombres de sensores
            first_run = list(runs.values())[0]
            sensor_names = list(first_run.temperature_data.columns)
            
            constants_df = pd.DataFrame(constants, index=sensor_names, columns=sensor_names)
            errors_df = pd.DataFrame(errors, index=sensor_names, columns=sensor_names)
            
            self.calibration_constants[set_num] = constants_df
            self.calibration_errors[set_num] = errors_df
            
            print(f"  Constantes calculadas: {constants_df.shape}")
            print(f"  Promedio de offsets: {np.nanmean(np.abs(constants)):.4f} K")
            print(f"  Error promedio: {np.nanmean(errors):.4f} K")
        
        print(f"\nTotal sets con constantes: {len(self.calibration_constants)}")
    
    def save_results(self, output_file="calibration_results.xlsx"):
        """
        Guarda los resultados en un archivo Excel.
        
        Args:
            output_file: Nombre del archivo de salida
        """
        if not self.calibration_constants:
            print("No hay constantes calculadas para guardar")
            return
        
        print(f"\nGuardando resultados en {output_file}")
        
        with pd.ExcelWriter(output_file) as writer:
            for set_num in sorted(self.calibration_constants.keys()):
                # Guardar constantes
                sheet_name = f"Set_{int(set_num)}_Constants"
                self.calibration_constants[set_num].to_excel(writer, sheet_name=sheet_name)
                
                # Guardar errores
                sheet_name = f"Set_{int(set_num)}_Errors"
                self.calibration_errors[set_num].to_excel(writer, sheet_name=sheet_name)
        
        print(f"✓ Resultados guardados en {output_file}")
    
    def get_summary(self):
        """
        Genera un resumen de los resultados.
        
        Returns:
            DataFrame con estadísticas por set
        """
        summary = []
        for set_num in sorted(self.calibration_constants.keys()):
            constants = self.calibration_constants[set_num]
            errors = self.calibration_errors[set_num]
            
            summary.append({
                "CalibSetNumber": set_num,
                "N_Sensors": constants.shape[0],
                "N_Runs": len(self.runs_by_set[set_num]),
                "Mean_Offset_K": np.nanmean(np.abs(constants.values)),
                "Mean_Error_K": np.nanmean(errors.values),
                "Max_Offset_K": np.nanmax(np.abs(constants.values)),
                "Max_Error_K": np.nanmax(errors.values)
            })
        
        return pd.DataFrame(summary)

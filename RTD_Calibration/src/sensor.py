from typing import Optional


class Sensor:
    """
    Data class: almacena ID y constante de calibración de un sensor RTD.
    
    Esta clase solo ALMACENA datos. Los cálculos se hacen en utils.py o tree.py.
    
    Atributos:
        id: int - ID numérico del sensor RTD (ej: 48178)
        calibration_constant: float - constante calculada por Tree
    
    Ejemplo de uso futuro:
        >>> sensor = Sensor(48178)
        >>> sensor.calibration_constant = 0.000123  # Asignado por Tree
        >>> print(sensor)
        Sensor(id=48178, cal=0.000123)
    """
    
    def __init__(self, sensor_id: int):
        self.id = sensor_id
        self.calibration_constant: Optional[float] = None #no hace falta (por definir con los paths)
    
    def __repr__(self) -> str:
        """
        Representación del objeto.
        
        Ejemplo:
            >>> sensor = Sensor(48178)
            >>> print(sensor)
            Sensor(id=48178)
        """
        cal = f", cal={self.calibration_constant:.6f}" if self.calibration_constant else ""
        return f"Sensor(id={self.id}{cal})"


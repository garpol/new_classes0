class Sensor:
    """
    Data class: almacena ID de un sensor RTD.
    
    Esta clase solo almacena el ID del sensor. Las constantes de calibración
    se calculan y almacenan en estructuras externas (Tree, DataFrames).
    
    Atributos:
        id: int - ID numérico del sensor RTD (ej: 48178)
    
    Ejemplo de uso:
        >>> sensor = Sensor(48178)
        >>> print(sensor)  # Sensor(id=48178)
    """
    
    def __init__(self, sensor_id: int):
        self.id = sensor_id
    
    def __eq__(self, other):
        """
        Compara si dos sensores son iguales basándose en su ID.
        Esto permite usar == para comparar sensores.
        """
        return isinstance(other, Sensor) and self.id == other.id
    
    def __hash__(self):
        """
        Devuelve un código único para el sensor basado en su ID.
        Esto permite usar sensores como claves en diccionarios o elementos de sets.
        """
        return hash(self.id)
    
    def __repr__(self) -> str:
        """
        Representación del objeto cuando se imprime.
        Ejemplo: print(sensor) muestra "Sensor(id=48178)"
        """
        return f"Sensor(id={self.id})"


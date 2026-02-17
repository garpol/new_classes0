from typing import Dict, Optional, List
try:
    from .tree_entry import TreeEntry
except ImportError:
    from tree_entry import TreeEntry

class Tree:
    """
    Árbol de calibración que organiza TreeEntries en una jerarquía.

    Cada nodo del árbol es un TreeEntry. El árbol permite:
        - Acceso rápido a entradas por set_number
        - Definir un nodo raíz (normalmente el set de ronda 3)
        - Navegar entre padres e hijos
        - Calcular rondas de calibración (R1, R2, R3)
        - Imprimir de forma clara la estructura
    
    Estructura típica:
        R3 (Root) - Set 57
        ├── R2 - Sets 50, 51, 52, ...
        └── R1 - Sets 1, 2, 3, ...
    """
    
    def __init__(self):
        # Diccionario para acceso rápido: set_number -> TreeEntry
        self.entries: Dict[float, TreeEntry] = {}
        # Nodo raíz del árbol (normalmente R3 = ronda de referencia absoluta)
        self.root: Optional[TreeEntry] = None
    
    def add_entry(self, entry: TreeEntry):
        """Añade un TreeEntry al árbol usando su set_number como clave."""
        self.entries[entry.set_number] = entry
    
    def get_entry(self, set_number: float) -> Optional[TreeEntry]:
        """Obtiene un TreeEntry por su set_number. Devuelve None si no existe."""
        return self.entries.get(set_number)
    
    def set_root(self, entry: TreeEntry):
        """
        Define el nodo raíz del árbol (normalmente el set de ronda 3).
        También lo añade al diccionario de entries si no estaba.
        """
        self.root = entry
        self.add_entry(entry)
    
    def get_root(self) -> Optional[TreeEntry]:
        """Devuelve el nodo raíz del árbol."""
        return self.root
    
    def all_entries(self) -> List[TreeEntry]:
        """Devuelve todas las entradas del árbol."""
        return list(self.entries.values())
    
    def get_round(self, entry: TreeEntry) -> int:
        """
        Calcula la ronda de calibración de un entry basándose en su distancia al root.
        
        Rondas:
            - R3 (ronda 3): El root (referencia absoluta)
            - R2 (ronda 2): Hijos directos del root
            - R1 (ronda 1): Nietos del root
        
        Usa BFS (búsqueda en anchura) para calcular la distancia.
        """
        if not self.root:
            return 0
        
        # Si es el root, es ronda 3
        if entry == self.root:
            return 3
        
        # BFS (búsqueda en anchura) para calcular distancia al root
        from collections import deque
        queue = deque([(self.root, 3)])  # (entry, ronda)
        visited = {self.root.set_number}
        
        while queue:
            current, current_round = queue.popleft()
            
            # Revisar cada hijo del nodo actual
            for child in current.children_entries:
                if child.set_number not in visited:
                    visited.add(child.set_number)
                    if child == entry:
                        return current_round - 1  # Los hijos están una ronda abajo
                    queue.append((child, current_round - 1))
        
        return 0  # No conectado al root
    
    def get_entries_by_round(self, round_number: int) -> List[TreeEntry]:
        """Devuelve todas las entradas de una ronda específica (calculada dinámicamente)."""
        return [entry for entry in self.entries.values() if self.get_round(entry) == round_number]
    
    def __repr__(self) -> str:
        root_str = f"{self.root.set_number}" if self.root else "None"
        return f"Tree({len(self.entries)} entries, root={root_str})"
    
    def print_tree(self):
        """Imprime el árbol de forma jerárquica desde la raíz."""
        if not self.root:
            print("Tree is empty")
            return
        
        def _print_node(node: TreeEntry, level=0):
            indent = "  " * level
            print(f"{indent}- Set {node.set_number}, valid_sensors: {[s.id for s in node.get_valid_sensors()]}")
            for child in node.children_entries:
                _print_node(child, level + 1)

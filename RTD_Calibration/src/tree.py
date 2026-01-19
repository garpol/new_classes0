"""
Tree: Estructura jerárquica de calibración.
"""

from typing import Dict, List, Optional
from tree_entry import TreeEntry


class Tree:
    """Árbol de calibración que organiza TreeEntries. Debe tener un print(tree) para que se cree aunque no tenga aun 'runs'."""
    
    def __init__(self):
        self.entries: Dict[float, TreeEntry] = {}
        self.root: Optional[TreeEntry] = None
        self.entries_by_round: Dict[int, List[TreeEntry]] = {1: [], 2: [], 3: []}
    
    def add_entry(self, entry: TreeEntry):
        self.entries[entry.set_number] = entry
        if entry.round in self.entries_by_round:
            if entry not in self.entries_by_round[entry.round]:
                self.entries_by_round[entry.round].append(entry)
    
    def get_entry(self, set_number: float) -> Optional[TreeEntry]:
        return self.entries.get(set_number)
    
    def get_entries_by_round(self, round_num: int) -> List[TreeEntry]:
        return self.entries_by_round.get(round_num, [])
    
    def set_root(self, entry: TreeEntry):
        self.root = entry
    
    def get_root(self) -> Optional[TreeEntry]:
        return self.root
    
    def __repr__(self) -> str:
        root_str = f"{self.root.set_number}" if self.root else "None"
        return f"Tree({len(self.entries)} entries, root={root_str})"
    
    def __str__(self) -> str:
        lines = ["Tree Structure:", "=" * 70]
        round_names = {3: "Round 3 (Top)", 2: "Round 2 (Intermediate)", 1: "Round 1 (Base)"}
        
        for round_num in sorted(self.entries_by_round.keys(), reverse=True):
            entries = self.entries_by_round[round_num]
            if not entries:
                continue
            lines.append(f"\n{round_names.get(round_num)}:")
            for entry in sorted(entries, key=lambda e: e.set_number):
                sensor_preview = entry.sensors[:3] if len(entry.sensors) > 3 else entry.sensors
                sensor_str = f"{sensor_preview}..." if len(entry.sensors) > 3 else str(entry.sensors)
                root_marker = " [ROOT]" if entry == self.root else ""
                line = f"  Set {entry.set_number}{root_marker}: {sensor_str}"
                if entry.raised_sensors:
                    line += f" -> raised: {entry.raised_sensors}"
                if entry.parent_entries:
                    parent_ids = sorted([p.set_number for p in entry.parent_entries])
                    line += f" -> parents: {parent_ids}"
                lines.append(line)
        lines.append("\n" + "=" * 70)
        lines.append(f"Total: {len(self.entries)} entries")
        return "\n".join(lines)

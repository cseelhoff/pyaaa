from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Dict
from detailedunit import DetailedUnit
from unitquantity import UnitQuantity

@dataclass(eq=False)
class Connection:
    unitQuantities: List[UnitQuantity] = field(default_factory=list)
    getUnitQuantities: Dict[DetailedUnit, UnitQuantity] = field(default_factory=dict)

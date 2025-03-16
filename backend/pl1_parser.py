from enum import Enum
from typing import List, Set, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
import re

class PredicateType(Enum):
    """
    Enum reprezentujuci typy predikatov v predikátovej logike prvého rádu.
    """
    UNARY = 1
    BINARY = 2
    TERNARY = 3
    MULTI = 4

@dataclass
class Predicate:
    """
    Trieda reprezentujuca jeden predikat v predikátovej logike prvého rádu.
    """
    name: str            # Nazov predikatu (S₃, HE, MT, atd.)
    arguments: List[str]  # Argumenty predikatu (list, lebo zoznamy nie su hashovatelne)
    type: PredicateType  # Typ predikatu (UNARY, BINARY, TERNARY)
    
    def __init__(self, name: str, arguments: List[str]):
        """
        Inicializuje predikat so zadanym nazvom a argumentmi.
        
        Args:
            name: Nazov predikatu
            arguments: Zoznam argumentov predikatu
        """
        self.name = name
        self.arguments = arguments
        
        # Urcenie typu predikatu podla poctu argumentov
        if len(arguments) == 1:
            self.type = PredicateType.UNARY
        elif len(arguments) == 2:
            self.type = PredicateType.BINARY
        elif len(arguments) == 3:
            self.type = PredicateType.TERNARY
        else:
            self.type = PredicateType.MULTI
    
    def __str__(self) -> str:
        """
        Prevadza predikat na citatelny textovy retazec.
        
        Returns:
            Retazec reprezentujuci predikat, napr. "S₃(b₁)" alebo "HE(b₁, e₁)"
        """
        args_str = ", ".join(self.arguments)
        return f"{self.name}({args_str})"
    
    def __eq__(self, other):
        """
        Porovnava dva predikaty na zaklade ich semantickej ekvivalencie.
        
        Args:
            other: Iny predikat na porovnanie
            
        Returns:
            True ak su predikaty semanticky ekvivalentne, inak False
        """
        if not isinstance(other, Predicate):
            return False
        
        return (self.name == other.name and 
                self.arguments == other.arguments)
    
    def __hash__(self):
        """
        Vytvára hash hodnotu pre predikát, aby mohol byť použitý ako kľúč v množine alebo slovníku.
        
        Returns:
            Hash hodnota predikátu založená na jeho názve a argumentoch
        """
        # Vytvoríme tuple z názvu a argumentov, ktorý je hashable
        return hash((self.name, tuple(self.arguments)))

@dataclass
class Formula:
    """
    Trieda reprezentujuca formulu v predikátovej logike prvého rádu.
    Formula moze byt jednoduchy predikat alebo zlozena formula s logickymi spojkami.
    """
    predicates: Set[Predicate]  # Mnozina predikatov v formule
    operator: Optional[str] = None  # Logická spojka: ∧, ∨, →, ↔, ¬
    subformulas: List['Formula'] = field(default_factory=list)  # Inicializácia prázdnym zoznamom
    
    def __str__(self) -> str:
        """
        Prevadza formulu na citatelny textovy retazec.
        
        Returns:
            Retazec reprezentujuci formulu ako konjunkciu predikatov
        """
        if not self.operator and len(self.predicates) == 1:
            return str(next(iter(self.predicates)))
        
        if self.operator == "¬" and len(self.subformulas) == 1:
            return f"¬({str(self.subformulas[0])})"
        
        if self.operator and self.subformulas:
            return f"({' ' + self.operator + ' '.join([str(f) for f in self.subformulas])})"
        
        # Ak máme len predikáty bez operátora, spojíme ich konjunkciou
        return " ∧ ".join(str(p) for p in self.predicates)
    
    def get_all_predicates(self) -> List[Predicate]:
        """Vráti všetky predikáty vo formule vrátane tých v podformulách."""
        all_predicates = list(self.predicates)
        
        if self.subformulas:
            for subformula in self.subformulas:
                all_predicates.extend(subformula.get_all_predicates())
        
        return all_predicates

def parse_pl1_formula(text: str) -> Formula:
    """
    Parsuje text v symbolickej notacii predikátovej logiky prvého rádu na formulu.
    
    Podporuje symbolické predikáty:
    - Ι(x,y) - x je typu y (is_a)
    - Π(x,y) - x má časť y (has_part)
    - Α(x,y,z) - x má atribút y s hodnotou z (has_attribute)
    - Μ(x,y) - x musí mať časť y (must_have_part)
    - Ν(x,y) - x nesmie mať časť y (must_not_have_part)
    
    Args:
        text: Text v symbolickej notacii PL1
        
    Returns:
        Formula reprezentujuca parsovany text
    """
    if not text or not text.strip():
        raise ValueError("Prázdna formula")
    
    # Odstranenie komentarov a prazdnych riadkov
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith('%') and not line.startswith('#'):
            # Odstranenie komentarov za vyrazom
            if '%' in line:
                line = line.split('%')[0].strip()
            if '#' in line:
                line = line.split('#')[0].strip()
            lines.append(line)
    
    if not lines:
        raise ValueError("Formula neobsahuje žiadne platné riadky po odstránení komentárov")
    
    # Spojenie riadkov a nahradenie viacnasobnych medzier jednou
    text = ' '.join(lines)
    text = re.sub(r'\s+', ' ', text)
    
    # Nahradenie logickych spojok medzerami pre jednoduchsie parsovanie
    text = text.replace('∧', ' ∧ ')
    text = text.replace('∨', ' ∨ ')
    text = text.replace('¬', ' ¬ ')
    text = text.replace('→', ' → ')
    text = text.replace('↔', ' ↔ ')
    
    # Rozdelenie textu na tokeny
    tokens = text.split()
    
    if not tokens:
        raise ValueError("Formula neobsahuje žiadne tokeny po spracovaní")
    
    # Parsovanie predikatov
    predicates = set()
    
    # Najprv spojíme tokeny, ktoré môžu byť rozdelené
    i = 0
    while i < len(tokens):
        if '(' in tokens[i] and ')' not in tokens[i] and i + 1 < len(tokens):
            # Spojíme tokeny, ktoré patria k jednému predikátu
            j = i + 1
            while j < len(tokens) and ')' not in tokens[j]:
                tokens[i] += ' ' + tokens[j]
                j += 1
            
            if j < len(tokens):
                tokens[i] += ' ' + tokens[j]
                # Odstránime spojené tokeny
                tokens = tokens[:i+1] + tokens[j+1:]
        i += 1
    
    # Teraz spracujeme predikáty
    predicate_pattern = r'([^\s(]+)\s*\(\s*([^)]*)\s*\)'
    
    for token in tokens:
        # Preskočíme logické spojky
        if token in ['∧', '∨', '¬', '→', '↔']:
            continue
        
        # Hľadáme predikáty v tokene
        matches = re.findall(predicate_pattern, token)
        
        for match in matches:
            pred_name = match[0].strip()
            args_str = match[1].strip()
            
            # Rozdelenie argumentov
            if args_str:
                # Odstránime úvodzovky z argumentov, ak existujú
                args = []
                for arg in args_str.split(','):
                    arg = arg.strip()
                    if arg.startswith('"') and arg.endswith('"'):
                        arg = arg[1:-1]
                    elif arg.startswith("'") and arg.endswith("'"):
                        arg = arg[1:-1]
                    args.append(arg)
            else:
                args = []
            
            try:
                # Vytvorenie predikátu
                pred = Predicate(pred_name, args)
                predicates.add(pred)
            except Exception as e:
                print(f"Chyba pri vytváraní predikátu {pred_name}({args_str}): {str(e)}")
    
    if not predicates:
        # Skúsime alternatívny prístup - hľadáme všetky predikáty v celom texte
        all_matches = re.findall(r'([^\s(]+)\s*\(\s*([^)]*)\s*\)', text)
        
        for match in all_matches:
            pred_name = match[0].strip()
            args_str = match[1].strip()
            
            if args_str:
                args = [arg.strip() for arg in args_str.split(',')]
            else:
                args = []
            
            try:
                pred = Predicate(pred_name, args)
                predicates.add(pred)
            except Exception as e:
                print(f"Chyba pri vytváraní predikátu {pred_name}({args_str}): {str(e)}")
    
    if not predicates:
        raise ValueError("Neboli nájdené žiadne platné predikáty vo formule")
    
    # Vytvorenie formuly
    return Formula(predicates=predicates)

def parse_pl1_dataset(text: str) -> List[Formula]:
    """
    Parsuje text obsahujuci viacero formul oddelených prázdnymi riadkami.
    
    Args:
        text: Text obsahujuci viacero formul
        
    Returns:
        Zoznam formul
    """
    # Rozdelenie textu na jednotlive formuly
    formula_texts = re.split(r'\n\s*\n', text)
    
    # Parsovanie kazdej formuly
    formulas = []
    for formula_text in formula_texts:
        if formula_text.strip():
            formula = parse_pl1_formula(formula_text)
            if formula.predicates:
                formulas.append(formula)
    
    return formulas

# Priklad pouzitia:
if __name__ == "__main__":
    # Priklad symbolickej notacie PL1
    example_text = """
    S₃(b₁) ∧ MT(b₁, "3_series") ∧ BT(b₁, "sedan") ∧
    HE(b₁, e₁) ∧ HT(b₁, t₁) ∧ HD(b₁, d₁) ∧ TL(b₁, "sport_line") ∧
    D(e₁, 2.0) ∧ FT(e₁, "petrol") ∧ P(e₁, 135) ∧
    TT(t₁, "steptronic") ∧ DT(d₁, "rear_wheel")
    """
    
    formula = parse_pl1_formula(example_text)
    print(f"Parsovana formula: {formula}")
    print(f"Pocet predikatov: {len(formula.predicates)}")
    for predicate in formula.predicates:
        print(f"- {predicate}") 
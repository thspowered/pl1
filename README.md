# PL1 Learning System

Systém pre učenie konceptov pomocou symbolickej notácie predikátovej logiky prvého rádu (PL1).

## Popis projektu

Tento projekt implementuje systém pre učenie konceptov na základe pozitívnych a negatívnych príkladov. Využíva Winstonov algoritmus učenia konceptov a reprezentuje znalosti pomocou symbolickej notácie predikátovej logiky prvého rádu (PL1).

Hlavné funkcie systému:
- Parsovanie a spracovanie príkladov v symbolickej notácii PL1
- Učenie konceptov pomocou Winstonovho algoritmu
- Porovnávanie nových príkladov s naučeným modelom
- Vizualizácia naučeného modelu ako sémantickej siete

## Štruktúra projektu

```
pl1_project/
├── backend/              # Backend aplikácia
│   ├── app.py            # FastAPI aplikácia
│   ├── model.py          # Reprezentácia modelu
│   ├── pl1_parser.py     # Parser pre PL1 notáciu
│   └── learner.py        # Implementácia Winstonovho algoritmu
├── data/                 # Dátové súbory
│   └── sample_dataset.pl1 # Vzorový dataset
├── frontend/             # Frontend aplikácia (bude implementovaná neskôr)
├── requirements.txt      # Závislosti projektu
├── run.py                # Skript na spustenie aplikácie
└── README.md             # Dokumentácia projektu
```

## Inštalácia

1. Vytvorte a aktivujte virtuálne prostredie:
   ```
   python -m venv venv
   source venv/bin/activate  # Na Windows: venv\Scripts\activate
   ```

2. Nainštalujte závislosti:
   ```
   pip install -r requirements.txt
   ```

## Spustenie

Spustite aplikáciu pomocou skriptu `run.py`:
```
python run.py
```

Aplikácia bude dostupná na adrese `http://localhost:8000`.

## API Endpointy

- `GET /`: Základný endpoint pre kontrolu, či API beží
- `POST /api/upload-dataset`: Nahrá dataset príkladov vo formáte PL1
- `GET /api/dataset`: Vráti všetky príklady v datasete
- `POST /api/train`: Trénuje model použitím vybraných príkladov z datasetu
- `POST /api/compare`: Porovná príklad s naučeným modelom a vráti výsledok
- `GET /api/model`: Vráti aktuálne naučený model vo formáte vhodnom pre vizualizáciu
- `GET /api/training-history`: Vráti históriu trénovania modelu
- `POST /api/reset`: Resetuje naučený model a históriu trénovania

## Formát PL1 notácie

Príklady sú reprezentované v symbolickej notácii predikátovej logiky prvého rádu (PL1). Používame nasledujúce predikáty:

- **Ι(x,y)** - x je typu y (napr. Ι(c₁, BMW) - c₁ je typu BMW)
- **Π(x,y)** - x má časť y (napr. Π(c₁, e₁) - c₁ má časť e₁)
- **Α(x,y,z)** - x má atribút y s hodnotou z (napr. Α(e₁, power_kw, 190) - e₁ má atribút power_kw s hodnotou 190)
- **Μ(x,y)** - x musí mať časť y (povinné spojenie)
- **Ν(x,y)** - x nesmie mať časť y (zakázané spojenie)

Príklad:
```
Ι(c₁, BMW) ∧ Ι(c₁, Series5) ∧
Π(c₁, e₁) ∧ Ι(e₁, DieselEngine) ∧
Α(e₁, power_kw, 190) ∧ Α(e₁, fuel_type, diesel) ∧
Π(c₁, t₁) ∧ Ι(t₁, AutomaticTransmission)
```

## Licencia

Tento projekt je licencovaný pod MIT licenciou. 
# Prezentacja — ASD1-M2-14

## Archiwum prac i projektów studenckich Filii

### Cel

Lokalne, w pełni offline repozytorium prac studenckich, realizowane w ramach
przedmiotu *Algorytmy i struktury danych I*.

### Kluczowe elementy

- **Model danych** — `Work` (praca), niezmienne `id`, walidacja pól.
- **Wyszukiwanie liniowe** z filtrem AND i licznikiem sprawdzonych rekordów.
- **Sortowanie przez wstawianie** (Insertion Sort) bez `sorted()` / `.sort()`,
  z licznikiem porównań kluczy i śladem kroków.
- **Wykrywanie duplikatów** — normalizacja `.strip().lower()`, porównanie
  zbioru autorów niezależnie od kolejności, jawne potwierdzenie.
- **JSON** — eksport i dwuetapowy import z wersją formatu.
- **Scenariusze** — kontrolny, typowy, graniczny, większy.

### Uruchomienie

```bash
python server.py
# następnie http://127.0.0.1:8000
```

Plik do celów demonstracyjnych (działa w trybie offline).

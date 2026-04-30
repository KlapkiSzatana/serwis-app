# SerwisApp 🛠️

**SerwisApp** to kompleksowe oprogramowanie do zarządzania serwisem elektronicznym i komputerowym. Aplikacja pozwala na pełną kontrolę nad procesem naprawy – od przyjęcia sprzętu, przez dokumentację techniczną, aż po rozliczenie i wydanie urządzenia klientowi.

## ✨ Główne Funkcje

*   **Zarządzanie Zleceniami:** Pełna historia napraw, statusy zleceń oraz baza klientów.
*   **Projektant Wydruku (WYSIWYG):** Nowoczesny, wizualny edytor szablonów (Potwierdzenia przyjęcia, Raporty naprawy).
*   **Komunikacja:** Moduły do wysyłki powiadomień SMS oraz e-mail o statusie naprawy.
*   **Bezpieczeństwo:** Ochrona hasłem, system kopii zapasowych (backup) oraz szyfrowanie danych.
*   **Personalizacja:** Możliwość wstawienia własnego logo, danych firmy oraz edycji regulaminów (RODO).
*   **Technologia:** Zbudowane w oparciu o Python 3 oraz stabilną bibliotekę GUI – PySide6.

## 🚀 Instalacja (Arch Linux)

Projekt jest przygotowany do pracy na systemie Arch Linux i zawiera gotowy plik `PKGBUILD`.

1. **Pobierz repozytorium:**
   ```bash
   git clone https://github.com/KlapkiSzatana/serwis-app.git
   cd serwis-app
   ```
2. **Zbuduj i zainstaluj paczkę:**
   ```bash
   makepkg -si
   ```
   Komenda ta automatycznie pobierze wymagane zależności (PySide6, Pillow, Cryptography) i skonfiguruje skrót w menu systemowym.
   
## 📂 Struktura Projektu
serwis-app.py – Główny plik uruchomieniowy.

modules/ – Logika biznesowa (drukowanie, baza danych, backupy).

ui/ – Definicje interfejsu użytkownika.

actions/ – Zasoby graficzne (ikony, przyciski).

fonts/ – Niezbędne czcionki do poprawnego generowania wydruków.

## 🛠️ Wymagania (Dependencies)
Aplikacja wymaga Pythona w wersji 3.10+ oraz następujących bibliotek:

python-pyside6

python-pillow

python-cryptography

python-requests

python-barcode (opcjonalnie, dla kodów kreskowych)

## Dostępne również na Windows i MacOS

### Pobierz najnowszą wersję:

- [Pobierz dla Windows (Instalator)](https://github.com/KlapkiSzatana/serwis-app/releases/latest/download/BudgetApp_Setup.exe)
- [Pobierz dla macOS](https://github.com/KlapkiSzatana/serwis-app/releases/latest/download/BudgetApp_macos)

## 📝 Licencja
Projekt udostępniany na licencji GPL-3.0.

Autor: KlapkiSzatana

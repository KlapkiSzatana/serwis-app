# SerwisApp 🛠️

**SerwisApp** to kompleksowe oprogramowanie do zarządzania serwisem elektronicznym i komputerowym. Aplikacja pozwala na pełną kontrolę nad procesem naprawy – od przyjęcia sprzętu, przez dokumentację techniczną, aż po rozliczenie i wydanie urządzenia klientowi.

### Spis treści
- [Główne Funkcje](#główne-funkcje)
- [Budowa ze źródeł](#budowa-ze-źródeł)
- [Instalacja (Arch Linux)](#instalacja-arch-linux)
- [Instalacja (Arch z AUR)](#instalacja-arch-z-aur)
- [Struktura Projektu](#struktura-projektu)
- [Wymagania (Dependencies)](#wymagania-dependencies)
- [Dostępne również na Windows i macOS](#dostępne-również-na-windows-i-macos)
- [Licencja](#licencja)

## Główne Funkcje

*   **Zarządzanie Zleceniami:** Pełna historia napraw, statusy zleceń oraz baza klientów.
*   **Projektant Wydruku (WYSIWYG):** Nowoczesny, wizualny edytor szablonów (Potwierdzenia przyjęcia, Raporty naprawy).
*   **Komunikacja:** Moduły do wysyłki powiadomień SMS oraz e-mail o statusie naprawy.
*   **Bezpieczeństwo:** Ochrona hasłem, system kopii zapasowych (backup) oraz szyfrowanie danych.
*   **Personalizacja:** Możliwość wstawienia własnego logo, danych firmy oraz edycji regulaminów (RODO).
*   **Technologia:** Zbudowane w oparciu o Python 3 oraz stabilną bibliotekę GUI – PySide6.

## Budowa ze źródeł

Pełna instrukcja budowy lokalnej wersji developerskiej, binarki Linux oraz paczek `.deb` i `.rpm` znajduje się w [BUILD_FROM_SOURCE.md](BUILD_FROM_SOURCE.md).

# Instalacja (Arch Linux i pochodne)

Aplikacja jest dostępna w AUR w dwóch wersjach.  
Wybierz jedną z poniższych metod:

---

### OPCJA A: Szybka instalacja – Gotowa binarka

Instalujesz gotowy program.  
Nie potrzebujesz Pythona, bibliotek ani kompilacji.

Pobiera się i działa natychmiast.

Jeśli używasz pomocnika AUR (`yay` lub `paru`), wpisz:

```bash
yay -S serwis-app-bin
```

lub

```bash
paru -S serwis-app-bin
```

---

### OPCJA B: Instalacja ze źródeł

Program buduje się bezpośrednio z kodu źródłowego.

System automatycznie pobierze:
- środowisko Python,
- PySide6,
- Pillow,
- oraz wszystkie wymagane zależności.

Jeśli używasz pomocnika AUR (`yay` lub `paru`), wpisz:

```bash
yay -S serwis-app
```

lub

```bash
paru -S serwis-app
```

---

### OPCJA C: Ręczna instalacja przez PKGBUILD (Bez pomocników AUR)

Jeśli nie używasz `yay` ani `paru`, możesz pobrać paczkę ręcznie i zbudować ją przez `makepkg`.

### Wersja binarna

```bash
git clone https://aur.archlinux.org/serwis-app-bin.git
cd serwis-app-bin
makepkg -si
```

### Wersja ze źródła

```bash
git clone https://aur.archlinux.org/serwis-app.git
cd serwis-app
makepkg -si
```

---

## Uruchamianie

Po instalacji (niezależnie od wybranej opcji) aplikację uruchamiasz wpisując:

```bash
serwis-app
```

Możesz także uruchomić ją z menu aplikacji swojego środowiska graficznego.

---

## Odinstalowanie

Aby całkowicie usunąć aplikację z systemu:

### Wersja binarna (`-bin`)

```bash
sudo pacman -Rs serwis-app-bin
```

### Wersja ze źródła

```bash
sudo pacman -Rs serwis-app
```

---
   
## Struktura Projektu
serwis-app.py – Główny plik uruchomieniowy.

modules/ – Logika biznesowa (drukowanie, baza danych, backupy).

ui/ – Definicje interfejsu użytkownika.

actions/ – Zasoby graficzne (ikony, przyciski).

fonts/ – Niezbędne czcionki do poprawnego generowania wydruków.

## Wymagania (Dependencies)
Aplikacja wymaga Pythona w wersji 3.10+ oraz następujących bibliotek:

python-pyside6

python-pillow

python-cryptography

python-requests

python-barcode (opcjonalnie, dla kodów kreskowych)

## Dostępne również na Windows i MacOS

Wersje aplikacji na macOS oraz Windows są automatycznie kompilowane i publikowane przy użyciu GitHub Actions. Dzięki temu proces budowania pozostaje spójny i w pełni zautomatyzowany dla tych platform.

Głównym środowiskiem rozwoju oraz docelową platformą projektu pozostaje jednak **Arch Linux** — to na nim skupia się podstawowy nurt rozwoju i testowania.

### Pobierz najnowszą wersję:

- [Pobierz dla Windows (Instalator)](https://github.com/KlapkiSzatana/serwis-app/releases/latest/download/SerwisApp_Setup.exe)
- [Pobierz dla macOS](https://github.com/KlapkiSzatana/serwis-app/releases/latest/download/SerwisApp_macos.dmg)

## Licencja
Projekt udostępniany na licencji GPL-3.0.

Autor: KlapkiSzatana

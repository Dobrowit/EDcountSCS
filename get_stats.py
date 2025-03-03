#!/usr/bin/python3
import ijson
import json
import time
import gzip
import requests
import os
import decimal
from functools import wraps
from datetime import datetime
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.animation as animation

URL = "https://downloads.spansh.co.uk/galaxy_stations.json.gz"
PLIK_GZ = "galaxy_stations.json.gz"
PLIK_DATY = "last_download.json"
dzisiejsza_data = "2025-03-03"  # Możesz dynamicznie pobierać datę np. datetime.today().strftime("%Y-%m-%d")


# Dekorator do pomiaru czasu wykonania funkcji
def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Funkcja '{func.__name__}' wykonana w {end_time - start_time:.6f} sekundy")
        return result
    return wrapper

@measure_time
def trzeba_pobrac_plik():
    if not os.path.exists(PLIK_GZ) or not os.path.exists(PLIK_DATY):
        return True  # Brak pliku lub brak daty → pobierz

    # Odczyt zapisanej daty
    try:
        with open(PLIK_DATY, "r") as f:
            data = json.load(f)
            last_date = datetime.strptime(data.get("last_download", ""), "%Y-%m-%d").date()
        return last_date < datetime.today().date()  # Pobieramy tylko, jeśli zapisany dzień jest wcześniejszy niż dzisiaj
    except (json.JSONDecodeError, ValueError, KeyError):
        return True  # Błędny format pliku → pobierz

@measure_time
def zapisz_date_pobrania():
    with open(PLIK_DATY, "w") as f:
        json.dump({"last_download": datetime.today().strftime("%Y-%m-%d")}, f)

@measure_time
def pobierz_plik():
    print("Pobieranie pliku...")
    try:
        response = requests.get(URL, stream=True)
        response.raise_for_status()

        with open(PLIK_GZ, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("Pobieranie zakończone.")
        zapisz_date_pobrania()
    except requests.RequestException as e:
        print(f"Błąd pobierania pliku: {e}")

@measure_time
def count_system_colonisation_ships_stream(plik_gz):
    dzisiejsza_data = datetime.today().strftime("%Y-%m-%d")
    plik_wynikowy = f"colonisation_ships_{dzisiejsza_data}.json"

    if os.path.exists(plik_wynikowy):
        print(f"Plik {plik_wynikowy} już istnieje. Pomijam przetwarzanie.")
        return

    print("Zliczanie elementów i zapisywanie wyników...")
    licznik = 0
    pasujace_elementy = []

    try:
        with gzip.open(plik_gz, 'rt', encoding='utf-8') as f:
            for element in ijson.items(f, 'item'):
                stations = element.get('stations', [])
                if any(station.get('name') == "System Colonisation Ship" for station in stations):
                    licznik += 1
                    # Filtrowanie tylko wymaganych pól
                    wybrane_pola = {
                        "id64": element.get("id64"),
                        "name": element.get("name"),
                        "coords": element.get("coords"),
                        "population": element.get("population"),
                        "stations": [
                            {
#                                "name": station.get("name"),
                                "id": station.get("id"),
#                                "type": station.get("type"),
                            }
                            for station in stations if station.get("name") == "System Colonisation Ship"
                        ]
                    }
                    pasujace_elementy.append(wybrane_pola)

        print(f"Liczba pasujących elementów: {licznik}")

        # Zapis wyników do pliku JSON
        if pasujace_elementy:
            
            # Fragment kodu zapisującego JSON:    
            with open(plik_wynikowy, "w", encoding="utf-8") as f_out:
#                json.dump(pasujace_elementy, f_out, ensure_ascii=False, indent=4)
                json.dump(pasujace_elementy, f_out, ensure_ascii=False, indent=4, default=lambda o: float(o) if isinstance(o, decimal.Decimal) else str(o))
            print(f"Wyniki zapisano do pliku: {plik_wynikowy}")

    except (OSError, ijson.JSONError) as e:
        print(f"Błąd odczytu pliku: {e}")

def rysuj_wspolrzedne_3d(plik_json):
    if not os.path.exists(plik_json):
        print(f"Plik {plik_json} nie istnieje.")
        return

    try:
        with open(plik_json, "r", encoding="utf-8") as f:
            dane = json.load(f)

        # Pobranie współrzędnych
        x, y, z = [], [], []
        for entry in dane:
            coords = entry.get("coords", {})
            x.append(coords.get("x", 0))
            y.append(coords.get("y", 0))
            z.append(coords.get("z", 0))

        print(f"{len(x)} stars")

        # Tworzenie wykresu 3D
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='blue', marker='.', alpha=0.2)

        # Zaznaczenie punktu Sol (0,0,0)
        ax.scatter(0, 0, 0, c='yellow', marker='*', s=200, label="Sol")  # Większy punkt gwiazdkowy
        ax.text(0, 0, 0, "Sol", color='black', fontsize=12, fontweight='bold')
        
        # Opisy osi
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title("System Colonisation Ships - 3D Map")

        plt.show()

    except json.JSONDecodeError:
        print(f"Błąd odczytu JSON w pliku {plik_json}")

def rysuj_wspolrzedne_3d_z_animacja(plik_json):
    if not os.path.exists(plik_json):
        print(f"Plik {plik_json} nie istnieje.")
        return

    try:
        with open(plik_json, "r", encoding="utf-8") as f:
            dane = json.load(f)

        # Pobranie współrzędnych
        x, y, z = [], [], []
        for entry in dane:
            coords = entry.get("coords", {})
            x.append(coords.get("x", 0))
            y.append(coords.get("y", 0))
            z.append(coords.get("z", 0))

        print(f"{len(x)} stars")

        # Tworzenie wykresu 3D
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Punkty kolonizacyjne
        scatter = ax.scatter(x, y, z, c='blue', marker='.', alpha=0.2, label="Colonisation Ships")

        # Zaznaczenie punktu Sol (0,0,0)
        ax.scatter(0, 0, 0, c='yellow', marker='*', s=200, label="Sol")  # Większy punkt gwiazdkowy
        ax.text(0, 0, 0, "Sol", color='black', fontsize=12, fontweight='bold')

        # Opisy osi
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
#        ax.set_title("System Colonisation Ships - 3D Map (Animated)")
#        ax.legend()

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_zticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.grid(False)  # Wyłącza siatkę


        # Funkcja aktualizująca animację
        def update(frame):
            ax.view_init(elev=20, azim=frame)  # Rotacja wokół osi Y

        # Tworzenie animacji
        ani = animation.FuncAnimation(fig, update, frames=np.arange(0, 360, 2), interval=50, repeat=True)

        plt.show()

    except json.JSONDecodeError:
        print(f"Błąd odczytu JSON w pliku {plik_json}")

# Sprawdzenie i pobranie pliku jeśli trzeba
if trzeba_pobrac_plik():
    pobierz_plik()

count_system_colonisation_ships_stream(PLIK_GZ)
plik_wejsciowy = f"colonisation_ships_{dzisiejsza_data}.json"
rysuj_wspolrzedne_3d(plik_wejsciowy)
rysuj_wspolrzedne_3d_z_animacja(plik_wejsciowy)

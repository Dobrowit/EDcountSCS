#!/usr/bin/python3
import ijson
import json
import time
import gzip
import requests
import os
import decimal
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
from functools import wraps
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler


URL = "https://downloads.spansh.co.uk/galaxy_stations.json.gz"
PLIK_GZ = "galaxy_stations.json.gz"
PLIK_DATY = "last_download.json"
dzisiejsza_data = datetime.today().strftime("%Y-%m-%d")


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
                                "id": station.get("id"),
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
                json.dump(pasujace_elementy, f_out, ensure_ascii=False, indent=4, default=lambda o: float(o) if isinstance(o, decimal.Decimal) else str(o))
            print(f"Wyniki zapisano do pliku: {plik_wynikowy}")

    except (OSError, ijson.JSONError) as e:
        print(f"Błąd odczytu pliku: {e}")


# Funkcja obsługująca kliknięcia
def on_pick(event):
    ind = event.ind[0]
    print(ind)
    population = populations[ind]
    ax.text(x[ind], y[ind], z[ind], f'  {population}', color='red')
    fig.canvas.draw()
    

def rysuj_wspolrzedne_3d(plik_json, anim=True):
    if not os.path.exists(plik_json):
        print(f"Plik {plik_json} nie istnieje.")
        return

    try:
        with open(plik_json, "r", encoding="utf-8") as f:
            dane = json.load(f)

        # Pobranie współrzędnych
        x, y, z, populations = [], [], [], []
        for entry in dane:
            coords = entry.get("coords", {})
            x.append(coords.get("x", 0))
            y.append(coords.get("y", 0))
            z.append(coords.get("z", 0))
            populations.append(entry.get("population", 0))

        print(f"{len(x)} stars")

        # Normalizacja rozmiarów markerów na podstawie populacji
        min_pop = min(populations)
        max_pop = max(populations)
        print(f"population: {min_pop} - {max_pop}")

        # Unikaj dzielenia przez zero, jeśli min_pop == max_pop
        # if min_pop == max_pop:
            # sizes = [50] * len(populations)  # Stały rozmiar, jeśli wszystkie populacje są takie same
        # else:
            # sizes = [(50 * (pop - min_pop) / (max_pop - min_pop) + 10) for pop in populations]
        # print(sizes)

        # Skalowanie populacji do zakresu rozmiarów punktów
        scaler = MinMaxScaler(feature_range=(10, 1000))  # Zakres rozmiarów punktów od 10 do 100
        rozmiary = scaler.fit_transform(np.array(populations).reshape(-1, 1)).flatten()

        min_r = min(rozmiary)
        max_r = max(rozmiary)
        print(f"rozmiary: {min_r} - {max_r}")

        # Tworzenie wykresu 3D
        plt.rcParams['toolbar'] = 'none' # Wyłączenie paska narzędziowego
        fig = plt.figure(figsize=(14, 9))  # Ustawia rozmiar figury na 12x8 cali
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='yellow', s=rozmiary, marker='.', alpha=0.5, label="Colonisation Ships", picker=True)
        # ax.scatter(x, y, z, c='blue', s=1, marker='.', alpha=0.2, label="Colonisation Ships")

        # Zaznaczenie punktu Sol (0,0,0)
        # ax.scatter(0, 0, 0, c='yellow', marker='o', s=100, label="Sol")  # Większy punkt gwiazdkowy
        # ax.text(0, 0, 0, "Sol", color='black', fontsize=12, fontweight='bold')
        
        # Opisy osi
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        # ax.set_title("System Colonisation Ships - 3D Map")
        # ax.legend()

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_zticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.grid(False)  # Wyłącza siatkę

        # Ukrycie osi
        # ax.get_xaxis().set_visible(False)
        # ax.get_yaxis().set_visible(False)
        # ax.get_zaxis().set_visible(False)

        # Usunięcie obrysu sześcianu
        ax.grid(False)  # Wyłącza siatkę
        ax.set_axis_off()  # Wyłącza rysowanie osi

        # Ustawienie czarnego tła
        fig.patch.set_facecolor('black')  # Tło figury
        ax.set_facecolor('black')  # Tło osi
        ax.w_xaxis.set_pane_color((0, 0, 0, 1))
        ax.w_yaxis.set_pane_color((0, 0, 0, 1))
        ax.w_zaxis.set_pane_color((0, 0, 0, 1))

        if anim:
            # Funkcja aktualizująca animację
            def update(frame):
                ax.view_init(elev=20, azim=frame)  # Rotacja wokół osi Y

            # Tworzenie animacji
            ani = animation.FuncAnimation(fig, update, frames=np.arange(0, 360, 1), interval=50, repeat=True)

        # Połączenie funkcji obsługującej kliknięcia
        fig.canvas.mpl_connect('pick_event', on_pick)
        
        plt.show()

    except json.JSONDecodeError:
        print(f"Błąd odczytu JSON w pliku {plik_json}")


# Sprawdzenie i pobranie pliku jeśli trzeba
if trzeba_pobrac_plik():
    pobierz_plik()

count_system_colonisation_ships_stream(PLIK_GZ)
plik_wejsciowy = f"colonisation_ships_{dzisiejsza_data}.json"
rysuj_wspolrzedne_3d(plik_wejsciowy, False)

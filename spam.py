

import pyautogui


import time
import sys
import threading

def start_spammer(text, count, delay):
    print("\n[!] PRZYGOTOWANIE: Masz 5 sekund na kliknięcie w pole tekstowe (np. Notatnik)...")
    for i in range(5, 0, -1):
        print(f" Start za: {i}...")
        time.sleep(1)
    
    print("\n[+] ROZPOCZĘTO SPAMOWANIE...")
    
    # Funkcja bezpieczeństwa PyAutoGUI: przesunięcie myszy w lewy górny róg ekranu przerywa program
    pyautogui.FAILSAFE = True 

    # Próba załadowania modułu keyboard do globalnego nasłuchu klawiszy.
    try:
        import keyboard
        KEYBOARD_AVAILABLE = True
    except Exception:
        KEYBOARD_AVAILABLE = False

    # Wątek nasłuchujący klawisz 'd' (globalnie z keyboard lub lokalnie w konsoli z msvcrt)
    stop_event = threading.Event()

    def _listen_for_d(ev):
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.wait('d')
                ev.set()
            except Exception:
                return
        else:
            try:
                import msvcrt
                while not ev.is_set():
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch.lower() == 'd':
                            ev.set()
                            break
                    time.sleep(0.1)
            except Exception:
                return

    listener = threading.Thread(target=_listen_for_d, args=(stop_event,), daemon=True)
    listener.start()

    i = 1
    # Jeśli count jest None oznacza to 'bez ograniczeń' — wysyłaj dopóki użytkownik nie przerwie
    try:
        while True:
            # Wpisanie zdefiniowanego tekstu
            pyautogui.write(text)

            # Symulacja naciśnięcia klawisza Enter w celu wysłania/przejścia do nowej linii
            pyautogui.press('enter')

            # Jeśli wciśnięto 'd' w wątku nasłuchu - zatrzymujemy spamera
            if stop_event.is_set():
                print("\n[!] WYŁĄCZONO: Naciśnięto 'd' — zatrzymano spamowanie.")
                break

            if count is None:
                print(f"  -> Wysłano wiadomość {i}")
            else:
                print(f"  -> Wysłano wiadomość {i}/{count}")

            # Przerwa między wiadomościami
            time.sleep(delay)

            if count is not None and i >= count:
                break

            i += 1

    except pyautogui.FailSafeException:
        print("\n[!] AWARYJNE PRZERWANIE: Wykryto ruch myszy w róg ekranu.")
        sys.exit()
    except KeyboardInterrupt:
        print("\n[!] PRZERWANIE PRZEZ UŻYTKOWNIKA: Zatrzymano spamowanie.")
        sys.exit()

def print_logo():
    print("""
    MMMMM  CCCCC  TTTTTT  OOOOO  OOOOO  L       SSSSS
    M   M  C      T     O   O  O   O  L       S
    M   M  C      T     O   O  O   O  L       S
    M   M  C      T     O   O  O   O  L       SSSSS
    M   M  C      T     O   O  O   O  L           S
    M   M  C      T     O   O  O   O  L           S
    M   M  CCCCC  T      OOOO   OOOO   LLLLLL  SSSSS
    """)


if __name__ == "__main__":
    print_logo()
    print("=== TESTOWY AUTOMAT WIADOMOŚCI (SPAMMER) ===")
    
    # Konfiguracja parametrów testu
    wiadomosc = input("Podaj treść wiadomości: ")
    ilosc_input = input("Ile razy wysłać wiadomość? (0 = bez ograniczeń): ")
    odstep = float(input("Podaj odstęp czasowy w sekundach (np. 0.5): "))

    try:
        ilosc = int(ilosc_input)
    except ValueError:
        print("[!] Błędne parametry wejściowe: 'Ilość' musi być liczbą całkowitą.")
        sys.exit()

    if ilosc < 0 or odstep < 0:
        print("[!] Błędne parametry wejściowe.")
        sys.exit()

    # 0 oznacza brak ograniczeń — przekazujemy None
    if ilosc == 0:
        ilosc = None

    start_spammer(wiadomosc, ilosc, odstep)
    print("\n[+] Test zakończony pomyślnie.")

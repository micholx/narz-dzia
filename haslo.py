import random 
import string

# Parametry generowania


LICZBA_WYNIKOW = 200000000 # 20 milionów linii
DLUGOSC_CYFR = 22         # 8 cyfr w każdej linijce (daje zakres do 99 999 999)
NAZWA_PLIKU = "kombinacje_20mln_cyfr.txt"

print(f"Rozpoczynam generowanie {LICZBA_WYNIKOW:,} unikalnych kombinacji...")

# Zapis do pliku z użyciem buforowania dla maksymalnej prędkości
batch_size = 100000  # Zapis paczkami po 100 tys. linii
buffer = ""

with open(NAZWA_PLIKU, "w", encoding="utf-8") as file:
    for i in range(LICZBA_WYNIKOW):
        wynik = ""
        letters = [znak for znak in string.ascii_letters]
        for a in range(DLUGOSC_CYFR):
            wynik += letters.pop(random.randrange(len(letters)))
            # print(len(letters))  
        wynik += "\n"
             
        
        buffer += wynik
        
        # Co 100 tysięcy linii zrzucamy bufor na dysk
        if len(buffer) >= batch_size:
            file.writelines(buffer)
            buffer = ""
    print(buffer)
    # Zapisanie reszty z bufora, jeśli coś zostało
    if buffer:
        file.writelines(buffer)

print(f"Gotowe! Pomyślnie utworzono plik '{NAZWA_PLIKU}' z 20 milionami unikalnych kombinacji cyfr")

# todo's

- als er 2 agenda-items zijn, check of deze in dezeflde shift vallen en zo ja, voeg ze in de juiste volgorde toe aan ge
  agenda
    - even een test case voor schrijven?
- bestand opslaan als en openen doen aan de hand van de laatste keer dat je dat in de app deed
- dyflexis shift vars in config weg stoppen
  - nog in het config scherm laten zien
- de shift genereer logica in de lijst weg werken.. en dan ideaal dat hij meteen eventData update zodat je in details in
  real time mee kan kijken
- in details menu ook de mogelijkheid geven om meer kopjes te laten zien? alle waardes van een shift bv

- test schrijven op het verwijderen/syncen  van google
  overzicht geven van de te verwijderen agenda items, synchroniseren en updaten met bevestiging? verantwoordelijkheid verder naar de gebruiker verplaatsen
- kan deze lijst in real time geupdate worden...??
- evenementen te verwijderen?? kan niet via ics
- export config, geen dubbel check op overschrijven als het bestand al bestaat
- agenda id is te vinden in de cal, ook in config showen
  - als de gebruiker hier bij kan, betere check op agenda id doen

dyflexis herschrijven met gebruik van de eventData classe
# ter dev info

https://pyinstaller.org/en/stable/
pyinstaller --onefile --windowed --specpath=build --name=dycal-file --icon=favicon.icns Main.py
pyinstaller --onedir --windowed --specpath=build --name=Dycal-dir --noconfirm --icon=favicon.icns Main.py
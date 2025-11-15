# Vizsgaprojekt
 
## Projekt célja
 
Ez a projekt egy modern, interaktív szókincsfejlesztő webes alkalmazás oktatási célokra. Célja, hogy segítséget nyújtson a felhasználók számára idegen szavak megtanulásában, kezelésében, gyakorlásában és statisztikák vezetésében, a hagyományos papír alapú szókártyák kiváltása egy környezetbarátabb, digitális megoldással, amely intuitívabb funkcióival hatékonyabban támogatja a nyelvtanulást.
 
## Fő funkciók – Felhasználói interakciók
 
A program a következő főbb lehetőségeket biztosít számodra:
 
- **Szavak hozzáadása**  
  Saját szavakat és fordításokat adhatsz hozzá (a főmenüben vagy az "Új szó hozzáadása" gombbal).  
  Emellett automata szóajánló funkció is elérhető, amely új tanulnivaló szavakat ajánl számodra.
 
- **Szavak kezelése, szerkesztése, törlése**  
  A "Szavak kezelése" menüponton keresztül meglévő szavaidat szerkesztheted, átírhatod vagy törölheted.
 
- **Gyakorlás – random és tanuló mód**  
  Különböző gyakorló módokban tesztelheted tudásod (pl. "Random" vagy "Gyakorlás" gombok), ahol véletlenszerűen vagy tanulásra ajánlott szavakból kapsz feladatokat.
 
- **Szókártyák**  
  Megtekintheted szókártya nézetben is a szavakat, ahol a kártyák “átfordíthatók”, így gyorsabban memorizálhatod őket.
 
- **Automata szóajánlás**  
  Az “Új random szó” funkciók révén a program automatikusan javasol új, számodra releváns szavakat.
 
- **Statisztikák és fejlődés követése**  
  Megtekintheted saját tanulási statisztikáidat (összes szó, ismert szavak, gyakorlásra szoruló szavak, átlagos magabiztossági szint stb.) és akár részletesen, szavanként is böngészheted eredményeidet.
 
- **Segítség funkciók a gyakorlásban**  
  Gyakorlás során különböző segítségeket kérhetsz: válaszlehetőséget (multiple choice), magánhangzók megmutatását, vagy épp feladhatod a feladatot.
 
- **Nyelvváltás**  
  Bármikor módosíthatod a fordítás irányát, és választhatsz a tanult és célnyelv között.
 
## Alap struktúra
 
- `app.py`: A backend fő Python fájlja (Flask szerver).
- `templates/`: HTML sablonok (pl. főoldal, gyakorlás, új szó, szókártyák, szerkesztés, statisztika stb.).
- `static/`: Statikus erőforrások (CSS, JavaScript, képek).
- `etc/`: Segédanyagok, konfigurációk, Belső dokumentáció..
 
## Használat
 
1. Telepítsd a szükséges Python csomagokat.
2. Indítsd el az alkalmazást:
   ```bash
   python app.py
   ```
3. A böngésződben elérhető lesz a felület (általában: `http://localhost:5000`).
4. Jelentkezz be vagy regisztrálj, majd kezdd el a szavak hozzáadását, gyakorlását, statisztikáid megtekintését!
 
## Szükséges függőségek
 
A projektben használt csomagok a `app.py` felépítése alapján Python és a kapcsolódó könyvtárak.

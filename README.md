# domoticz-ev-charger-timer

Python plugin for Domoticz to provide simple time-based control of an EV charger.

The plugin switches a selected Domoticz device ON or OFF according to the configured time schedule.

Similar functionality can also be achieved using the standard Domoticz switch timer, but this plugin provides a dedicated and easily manageable EV charging timer that can be temporarily disabled without modifying the configured schedule.

It also includes a safety function that prevents the charger from being switched ON again within 30 minutes after it has been switched OFF.

This helps avoid frequent OFF/ON cycling of the EV charger and the vehicle's onboard charger.

# Features

- Time-based EV charger control
- Configurable ON / OFF periods
- Easy temporary disabling of scheduled charging
- Minimum 30-minute delay before the charger can be switched ON again after switching OFF
- Uses a standard Domoticz switch device for charger control

# Prerequisites

- Domoticz 2022.1 or newer
- Domoticz with Python plugin support enabled  
  https://www.domoticz.com/wiki/Using_Python_plugins

# Installation

You can install the plugin manually or by using the
[Domoticz Plugins Manager](https://github.com/stas-demydiuk/domoticz-plugins-manager).

## Manual installation

1. Clone or copy the plugin into your Domoticz plugins directory:

    ```bash
    cd domoticz/plugins
    git clone https://github.com/szelessavalapitvany/EV_Charge_Control
    ```

2. Restart Domoticz.

3. Make sure **Accept new Hardware Devices** is enabled in Domoticz settings.

4. Go to **Setup → Hardware**.

5. Add a new hardware device using the EV Charger Timer plugin.

6. Configure the required parameters:

    - Domoticz switch used to control the EV charger
    - charging / switching time period
    - required operating mode

The plugin controls the selected switch according to the configured schedule.

If the charger has been switched OFF, the safety function prevents it from being switched ON again for 30 minutes.

## Plugin update

1. Go to the plugin directory and pull the latest version:

    ```bash
    cd domoticz/plugins/EV_Charge_Control
    git pull
    ```

2. Restart Domoticz.

Note:  
If you modified plugin files and `git pull` fails, you can stash local changes:

```bash
git stash
```

## Plugin downgrade

1. Reset the plugin to an earlier version:

    ```bash
    cd domoticz/plugins/EV_Charge_Control
    git reset --hard <commit_hash>
    ```

2. Restart Domoticz.

Alternatively, disable and re-enable the plugin under **Setup → Hardware**. Browser cache cleanup may be required.

---

# domoticz-ev-charger-timer (magyarul)

Python plugin Domoticzhoz elektromosautó-töltő egyszerű időalapú vezérlésére.

A plugin a beállított időszak alapján egy kiválasztott Domoticz kapcsolót be- vagy kikapcsol.

Hasonló működés a Domoticz hagyományos kapcsoló-időzítésével is megoldható, de ezzel a pluginnal az autótöltés időzítése külön kezelhető, ezért egyszerűen és ideiglenesen kikapcsolható anélkül, hogy a beállított időpontokat módosítani kellene.

A plugin egy biztonsági funkciót is tartalmaz: kikapcsolás után 30 percig nem engedi újra bekapcsolni a töltőt.

Ez csökkenti a töltő és az autó fedélzeti töltőjének túl gyakori ki- és bekapcsolását.

# Funkciók

- Időalapú autótöltő-vezérlés
- Beállítható be- és kikapcsolási időszak
- Az időzített működés egyszerű ideiglenes kikapcsolása
- Kikapcsolás után minimum 30 perces várakozási idő az újbóli bekapcsolás előtt
- Hagyományos Domoticz kapcsoló használata a töltő vezérlésére

# Előfeltételek

- Domoticz 2022.1 vagy újabb
- Python plugin támogatás engedélyezve a Domoticzban  
  https://www.domoticz.com/wiki/Using_Python_plugins

# Telepítés

A plugin telepíthető manuálisan vagy a
[Domoticz Plugins Manager](https://github.com/stas-demydiuk/domoticz-plugins-manager) segítségével.

## Manuális telepítés

1. Másold / klónozd a plugint a Domoticz plugin könyvtárába:

    ```bash
    cd domoticz/plugins
    git clone https://github.com/szelessavalapitvany/EV_Charge_Control
    ```

2. Indítsd újra a Domoticzot.

3. Ellenőrizd, hogy az **Accept new Hardware Devices** engedélyezve van.

4. Lépj a **Setup → Hardware** menübe.

5. Add hozzá az új hardvert az EV Charger Timer pluginnal.

6. Állítsd be a szükséges paramétereket:

    - az autótöltőt vezérlő Domoticz kapcsolót
    - a be- / kikapcsolási időszakot
    - a kívánt működési módot

A plugin a megadott időzítés alapján vezérli a kiválasztott kapcsolót.

Ha a töltő kikapcsolásra került, a biztonsági funkció 30 percig nem engedi annak újbóli bekapcsolását.

## Plugin frissítése

1. Lépj be a plugin könyvtárába és frissítsd:

    ```bash
    cd domoticz/plugins/EV_Charge_Control
    git pull
    ```

2. Indítsd újra a Domoticzot.

Megjegyzés:  
Ha módosítottad a plugin fájljait és a `git pull` nem fut le, a helyi változtatások eltárolhatók:

```bash
git stash
```

## Plugin visszaléptetése (downgrade)

1. Régebbi verzió visszaállítása:

    ```bash
    cd domoticz/plugins/EV_Charge_Control
    git reset --hard <commit_hash>
    ```

2. Indítsd újra a Domoticzot.

Alternatív megoldásként a plugin letiltható, majd újra engedélyezhető a **Setup → Hardware** menüben. Böngésző-cache törlés szükséges lehet.

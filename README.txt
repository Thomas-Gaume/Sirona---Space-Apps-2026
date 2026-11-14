Infos d'un site lunaire

Calcule, pour un site à la surface de la Lune et une plage de dates, la position de la Terre et du Soleil dans le ciel depuis la Lune, la possibilité de communiquer en direct avec la Terre, la fraction du Soleil visible et le flux solaire reçu sur une surface.
Les positions viennent des éphémérides NASA/JPL via SPICE


SI PREMIERE UTILISATION : LANCER FONCTION "download_files" DANS "download_files.py" !!!!!!!


Structure :


main.py - Lit les paramètres, calcule et renvoie les informations via la variable `r`
calc.py - Calcule "site_info" (un instant), "site_range" (une plage), "format_info" (texte)
viewer.py - Aperçu des positions de chaque corps (Terre, Lune, Soleil) avec slider temporel
sites.py - Dictionnaire "sites". Nom et (latitude, longitude)
load_kernels.py - Charge les kernels SPICE
download_files.py - Télécharge les kernels nécessaires
constants.py - Rayons, constante solaire `S0`, `AU`, `ABCORR`, etc.
geometry.py - Base locale Est/Nord/Zenith, vecteur du site, azimut/élévation
eclairement.py -  Fraction de Soleil au-dessus de l'horizon, recouvrement Soleil/Terre

Modules : 

urllib
datetime
spiceypy
numpy
matplotlib


Output : 

r : liste de dictionnaires. Indice 0 correspond à l'instant initial. Un dictionnaire par pas de temps. Taille : int(days * 24 / step_hours) + 1

utc : str. Instant du calcul, arrondi à la seconde (ex. `"2026-12-22T00:00:00"`)
el_earth : float.  Élévation de la Terre sur l'horizon local (0° = horizon, 90° = zénith, négatif = sous l'horizon).
az_earth : float. Azimut de la Terre, depuis le Nord vers l'Est (0° N, 90° E, 180° S, 270° O) |
dist_earth_km : float. Distance site au centre de la Terre
el_sun : float. Élévation du centre du Soleil. Degrés.
az_sun : float. Azimut du Soleil (même convention que "az_earth"). Degrés
dist_sun_km : float. Distance site au centre du Soleil 
sun_fraction : float. Fraction du disque solaire visible (horizon et éclipse par la Terre). 1 = entier, 0 = rien
flux_W_m2 : float. Flux solaire sur une surface **horizontale** : "S0 × (AU/d)² × sun_fraction × sin(el_sun)". 0 si le Soleil est sous l'horizon
can_communicate : bool. True si el_earth > earth_min_el
sun_up : bool. True si sun_fraction > 0

Exemple :

{'utc': '2026-12-22T00:00:00',
 'el_earth': 60.91, 'az_earth': 255.10, 'dist_earth_km': 360496.13,
 'el_sun': 87.84, 'az_sun': 152.42, 'dist_sun_km': 147475974.90,
 'sun_fraction': 1.0, 'flux_W_m2': 1399.45,
 'can_communicate': True, 'sun_up': True}

Ajouter un site :

Dans `sites.py`, ajouter une entrée `nom: (latitude, longitude)`. Latitude en degrés (Nord positif), longitude en degrés (Est positif), repère Mean Earth. Éviter ±90° exact !

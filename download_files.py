import urllib.request

def download_files() : 
    BASE = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
    FILES = {
        "naif0012.tls": "lsk/", #Temps (pour faire UTC -> Temps ephemerides)
        "de440.bsp": "spk/planets/", #Positions (Terre, Lune, Soleil)
        "pck00011.tpc": "pck/", #Constantes
        "moon_pa_de440_200625.bpc": "pck/", #Orientation Lune
        "moon_de440_220930.tf": "fk/satellites/a_old_versions/", #Definitions reperes (passer de Lune inertiel à Lune mean earth)
    }
    for name, folder in FILES.items():
        print("Téléchargement", name)
        urllib.request.urlretrieve(BASE + folder + name, name)


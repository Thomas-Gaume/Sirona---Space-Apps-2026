import numpy as np

def sun_fraction_horizon(el_deg, rho, horizon_deg=0.0):
    #Fraction de la surface de la Terre visible
    #rho est le demi-angle sous lequel on voit l'astre. rho = arcsin(R/d)
    x = np.clip(np.radians(el_deg - horizon_deg) / rho, -1.0, 1.0)
    return (np.arccos(-x) + x * np.sqrt(1.0 - x * x)) / np.pi #L’aire d’un disque de rayon 1 au-dessus d’une droite située à la hauteur c 


def disc_overlap_area(r1, r2, d):
    #Vérifie si la Terre est devant la Lune
    #r1 : rayon angulaire du Soleil
    #r2 : rayon angulaire Terre
    #d : séparation angulaire
    if d >= r1 + r2: 
        return 0.0
    if d <= abs(r1 - r2):
        return np.pi * min(r1, r2) ** 2
    a1 = r1**2 * np.arccos((d**2 + r1**2 - r2**2) / (2 * d * r1))
    a2 = r2**2 * np.arccos((d**2 + r2**2 - r1**2) / (2 * d * r2))
    tri = 0.5 * np.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a1 + a2 - tri
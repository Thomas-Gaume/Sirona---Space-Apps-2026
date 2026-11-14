import numpy as np
import spiceypy as sp

from geometry import site_vector
from calc import format_info, site_info
from constants import R_MOON

def run_viewer(lat, lon, start_utc, days, earth_min_el):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Wedge
    from matplotlib.widgets import Slider

    et0 = sp.str2et(start_utc)
    FRAME = "ECLIPJ2000"
    LIM = 620_000.0 # km, demi-largeur de la vue
    D_EARTH, D_MOON, D_SUN = 38_000.0, 22_000.0, 45_000.0 # rayons d'affichage (exagérés)
    SUN_DIST_DISP = 540_000.0 # distance d'affichage du Soleil (non à l'échelle)

    # Orbite de la Lune sur la plage (pas de 1 h)
    t_orb = et0 + np.arange(0, days * 24 + 1) * 3600.0
    orbit = np.array([sp.spkpos("MOON", t, FRAME, "NONE", "EARTH")[0][:2] for t in t_orb])

    site = site_vector(lat, lon)

    def scene(ax, et, with_sun):
        ax.clear()
        ax.set_aspect("equal")
        ax.set_xlim(-LIM, LIM)
        ax.set_ylim(-LIM, LIM)
        ax.set_xticks([])
        ax.set_yticks([])

        moon = sp.spkpos("MOON", et, FRAME, "NONE", "EARTH")[0][:2]
        sun_vec = sp.spkpos("SUN", et, FRAME, "NONE", "EARTH")[0]
        sun_dir = sun_vec[:2] / np.linalg.norm(sun_vec[:2])
        sun_xy = sun_dir * SUN_DIST_DISP
        ang = np.degrees(np.arctan2(sun_dir[1], sun_dir[0]))

        ax.plot(orbit[:, 0], orbit[:, 1], ":", color="gray", lw=1)

        # Terre
        ax.add_patch(Circle((0, 0), D_EARTH, color="#1f3a5f"))
        if with_sun:
            ax.add_patch(Wedge((0, 0), D_EARTH, ang - 90, ang + 90, color="#4c9be8"))
        else:
            ax.add_patch(Circle((0, 0), D_EARTH, color="#4c9be8"))

        # Lune
        ax.add_patch(Circle(moon, D_MOON, color="#3a3a3a"))
        if with_sun:
            ax.add_patch(Wedge(moon, D_MOON, ang - 90, ang + 90, color="#d8d8d8"))
        else:
            ax.add_patch(Circle(moon, D_MOON, color="#d8d8d8"))

        # Site (projeté sur le disque lunaire vu du dessus)
        rot = sp.pxform("MOON_ME", FRAME, et)
        s = rot @ site
        spt = moon + s[:2] / R_MOON * D_MOON
        ax.plot(*spt, "o", ms=6, mfc="red" if s[2] > 0 else "none", mec="red")

        if with_sun:
            ax.add_patch(Circle(sun_xy, D_SUN, color="#ffd93b"))
            for target in ((0, 0), moon):
                ax.plot([sun_xy[0], target[0]], [sun_xy[1], target[1]],
                        "-", color="#ffd93b", alpha=0.25, lw=1)
            ax.text(sun_xy[0], sun_xy[1] - D_SUN * 1.8, "Soleil\n(non à l'échelle)",
                    ha="center", va="top", fontsize=8, color="#ffd93b")

        d_em = np.linalg.norm(moon)
        ax.text(0, -LIM * 0.95, f"Distance Terre-Lune : {d_em:,.0f} km".replace(",", " "),
                ha="center", fontsize=8)

    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7.5))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.27, wspace=0.05)
    info_txt = fig.text(0.5, 0.03, "", ha="center", va="bottom", fontsize=10,
                        family="monospace")

    ax_sl = fig.add_axes([0.15, 0.17, 0.7, 0.03])
    slider = Slider(ax_sl, "Jours\ndepuis début", 0, days, valinit=0, valstep=1 / 24)

    def update(val):
        et = et0 + slider.val * 86400.0
        scene(ax1, et, with_sun=False)
        scene(ax2, et, with_sun=True)
        ax1.set_title("Terre – Lune", fontsize=11)
        ax2.set_title("Terre – Lune – Soleil", fontsize=11)
        info_txt.set_text(format_info(site_info(et, lat, lon, earth_min_el),
                                      lat, lon, earth_min_el))
        fig.canvas.draw_idle()

    def on_key(event):
        steps = {"right": 1 / 24, "left": -1 / 24, "up": 1.0, "down": -1.0}
        if event.key in steps:
            slider.set_val(float(np.clip(slider.val + steps[event.key], 0, days)))

    fig.canvas.mpl_connect("key_press_event", on_key)
    slider.on_changed(update)
    update(0)
    plt.show()
    
if __name__ == "__main__":
    from main import site_simu, date_UTC, start_utc, lat, lon, earth_min_el
    from load_kernels import load_kernels

    load_kernels()
    try:
        run_viewer(lat, lon, start_utc, 30, earth_min_el)
    finally:
        sp.kclear()

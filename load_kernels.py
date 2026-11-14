import os
import spiceypy as sp

KERNELS = ["naif0012.tls", "de440.bsp", "pck00011.tpc",
           "moon_pa_de440_200625.bpc", "moon_de440_220930.tf"]

def find_kernel_dir():
    candidates = [os.environ.get("KERNEL_DIR"),
                  os.path.dirname(os.path.abspath(__file__)),
                  os.getcwd()]
    for d in candidates:
        if d and os.path.exists(os.path.join(d, "de440.bsp")):
            return d
    raise FileNotFoundError("de440.bsp introuvable : mets les kernels à côté du script "
                            "ou définis KERNEL_DIR.")

def load_kernels(): 
    d = find_kernel_dir()
    sp.furnsh([os.path.join(d, k) for k in KERNELS])

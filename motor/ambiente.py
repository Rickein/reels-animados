"""Prepara o ambiente: acha o ffmpeg e deixa as bibliotecas da NVIDIA visiveis para a GPU."""
import glob
import os
import shutil
import site
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_MODELOS = RAIZ / "modelos"

# o Windows sem "modo desenvolvedor" nao cria symlinks; o cache do Hugging Face funciona igual, so avisa
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

_gpu_preparada = False


def achar_ffmpeg(nome: str = "ffmpeg") -> str:
    """Caminho do ffmpeg (ou ffprobe). Funciona mesmo em terminais abertos antes da instalacao."""
    caminho = shutil.which(nome)
    if caminho:
        return caminho
    # o winget cria um atalho aqui, mas o PATH so e atualizado em terminais novos
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    atalho = local / "Microsoft" / "WinGet" / "Links" / f"{nome}.exe"
    if atalho.exists():
        return str(atalho)
    for exe in (local / "Microsoft" / "WinGet" / "Packages").glob(f"Gyan.FFmpeg*/**/bin/{nome}.exe"):
        return str(exe)
    raise FileNotFoundError(f"{nome} nao encontrado. Instale com: winget install Gyan.FFmpeg.Essentials")


def preparar_gpu() -> None:
    """No Windows, registra as pastas de DLL do cuBLAS/cuDNN instalados pelo pip (pacotes nvidia-*)."""
    global _gpu_preparada
    if _gpu_preparada or os.name != "nt":
        return
    bases = site.getsitepackages() + [site.getusersitepackages()]
    for base in bases:
        for pasta in glob.glob(os.path.join(base, "nvidia", "*", "bin")):
            os.add_dll_directory(pasta)
            os.environ["PATH"] = pasta + os.pathsep + os.environ.get("PATH", "")
    _gpu_preparada = True


def gpu_disponivel() -> bool:
    preparar_gpu()
    import ctranslate2
    return ctranslate2.get_cuda_device_count() > 0

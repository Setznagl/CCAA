"""Prévia estática Fast Track: preserva os bytes do modelo, sem ler bases."""
from pathlib import Path


def render_fast_track(root):
    for folder in ('AGENDA_FAST_TRACK_INFRA_2026', 'FAST_TRACK_INFRA_2026'):
        path = Path(root) / 'fluxos' / folder / 'modelo_email.html'
        if path.is_file():
            return path.read_bytes()
    raise FileNotFoundError('Modelo HTML da AGENDA_FAST_TRACK_INFRA_2026 não encontrado')

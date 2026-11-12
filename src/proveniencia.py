"""
proveniencia.py
---------------
Manifest de procedência: todo arquivo de dados do pipeline tem um .manifest.json ao lado
dizendo de onde veio. O dashboard só aceita dados com origem "ons_bigquery".
"""

import hashlib
import json
from pathlib import Path

ORIGEM_REAL = "ons_bigquery"
ORIGEM_SINTETICA = "synthetic"


class ProvenienciaError(RuntimeError):
    """Arquivo de dados sem manifest, ou com origem diferente da esperada."""


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def caminho_manifest(arquivo: Path) -> Path:
    arquivo = Path(arquivo)
    return arquivo.with_name(arquivo.stem + ".manifest.json")


def escrever_manifest(arquivo: Path, dados: dict) -> Path:
    destino = caminho_manifest(arquivo)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def ler_manifest(arquivo: Path, origem_esperada: str) -> dict:
    """Lê o manifest e confere a origem. Falha com mensagem clara, nunca assume."""
    caminho = caminho_manifest(arquivo)
    if not caminho.exists():
        raise ProvenienciaError(
            f"Sem manifest para {Path(arquivo).name} (esperado: {caminho.name}). "
            "Dado sem procedência registrada não é aceito. Rode src/ingestao.py."
        )
    manifest = json.loads(caminho.read_text(encoding="utf-8"))
    if manifest.get("origem") != origem_esperada:
        raise ProvenienciaError(
            f"{Path(arquivo).name} tem origem '{manifest.get('origem')}', esperado '{origem_esperada}'."
        )
    return manifest

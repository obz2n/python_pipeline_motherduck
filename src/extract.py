import os
from pathlib import Path

import chardet
import pandas as pd
from loguru import logger

try:
    from .config import ENCODINGS
except ImportError:
    from config import ENCODINGS

# ============================================================
# Extração de dados
# ============================================================
def detectar_encoding(file_path: Path, amostra_bytes: int = 50_000) -> str:
    """
    Detecta o encoding do arquivo usando chardet.
    Lê apenas os primeiros `amostra_bytes` bytes para ser eficiente em arquivos grandes.
    Retorna o encoding detectado ou 'cp1252' como padrão seguro para BR.
    """
    try:
        with open(file_path, "rb") as f:
            amostra = f.read(amostra_bytes)

        resultado = chardet.detect(amostra)
        encoding = resultado.get("encoding") or "utf-8"
        confianca = resultado.get("confidence", 0)

        logger.debug(f"  Encoding detectado: '{encoding}' (confiança: {confianca:.0%})")

        if confianca < 0.7:
            logger.debug("  Confiança baixa — usando 'cp1252' como fallback seguro")
            return "cp1252"

        return encoding
    except Exception as e:
        logger.warning(
            f"  Erro ao detectar encoding: {e}. Usando 'cp1252' como padrão."
        )
        return "cp1252"


def tentar_ler_com_separador(file_path: Path, encoding: str, sep: str) -> pd.DataFrame | None:
    for engine in ("c", "python"):
        try:
            df = pd.read_csv(
                file_path,
                sep=sep,
                encoding=encoding,
                engine=engine,
                keep_default_na=False,
            )
            if df.shape[1] <= 1:
                continue
            return df
        except Exception:
            continue

    return None

def ler_arquivo_csv(file_path: Path) -> pd.DataFrame | None:
    """
    Lê um arquivo CSV com suporte a diferentes separadores e encodings.
    Tenta primeiro o encoding detectado e, em seguida, os fallbacks da lista ENCODINGS.
    """
    logger.info(f"Lendo: {file_path.name}")
    encoding_detectado = detectar_encoding(file_path)

    for enc in [encoding_detectado, *ENCODINGS]:
        for sep in [";", ","]:
            try:
                df = tentar_ler_com_separador(file_path, enc, sep)
                if df is None:
                    continue

                logger.info(
                    f"  ✓ Lido com sucesso com encoding '{enc}' e separador '{sep}' "
                    f"({len(df):,} linhas, {len(df.columns)} colunas)"
                )
                return df
            except UnicodeDecodeError:
                logger.debug(f"  UnicodeDecodeError com '{enc}' — tentando próximo...")
            except Exception as e:
                logger.debug(f"  Erro ao ler com '{enc}' e separador '{sep}': {e}")

    logger.warning(f"  ⚠️ Não foi possível ler o arquivo: {file_path.name}")
    return None


def extrair_dados_bronze(file_path: str | Path) -> pd.DataFrame | None:
    """
    Extrai os dados da base de dados bronze.
    Retorna um DataFrame contendo os dados extraídos da base bronze, ou None se o
    arquivo não existir ou não puder ser lido.
    """
    logger.info("Extraindo dados da base de dados bronze...")
    if not file_path:
        logger.warning("  Caminho do arquivo não fornecido.")
        return None

    path = Path(file_path)
    if not path.is_file():
        logger.warning(f"  Arquivo não encontrado: {path}")
        return None

    return ler_arquivo_csv(path)
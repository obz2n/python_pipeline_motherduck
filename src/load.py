import duckdb
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import loguru

from config import DB

logger = loguru.logger

# Procurar .env na raiz do projeto (pai do diretório src/)
env_path = Path(__file__).parent.parent / ".env"

if not env_path.exists():
    logger.warning(f"Arquivo .env não encontrado em {env_path}")

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path=env_path)
logger.debug(f"Carregando variáveis de ambiente de: {env_path}")

def conectar_motherduck():
    """Conecta ao banco de dados MotherDuck usando variáveis de ambiente."""
    logger.debug("Conectando ao banco de dados MotherDuck...")
    # Aqui você pode adicionar a lógica de conexão real, por exemplo, usando SQLAlchemy ou outro driver.
    # Exemplo fictício:
    connection = dotenv_values(env_path).get("NAME")
    token = dotenv_values(env_path).get("MOTHERDUCK_TOKEN")
    return connection, token

def carregar_dados(df, tabela: str, schema: str | None = None) -> int:
    """Carrega o DataFrame no MotherDuck e retorna o total de linhas gravadas."""

    _, token = conectar_motherduck()
    database = DB
    if not token:
        raise ValueError("MOTHERDUCK_TOKEN deve estar definido no .env")

    schema = schema or "main"
    destino = f'"{schema}"."{tabela}"'
    logger.debug(f"Carregando {len(df)} linhas em {database}.{schema}.{tabela}...")

    con = duckdb.connect(f"md:?motherduck_token={token}")
    try:
        con.execute(f'CREATE DATABASE IF NOT EXISTS "{database}"')
        con.execute(f'USE "{database}"')
        con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        con.register("df_carga", df)
        con.execute(f"CREATE OR REPLACE TABLE {destino} AS SELECT * FROM df_carga")
        total = con.execute(f"SELECT COUNT(*) FROM {destino}").fetchone()[0]
    finally:
        con.close()

    if total != len(df):
        raise RuntimeError(f"Contagem divergente: DataFrame={len(df)}, tabela={total}")
    logger.debug("Dados carregados com sucesso.")
    return total
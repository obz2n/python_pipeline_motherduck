import sys

from loguru import logger


from config import DATA_BRONZE_PATH, SCHEMA_NAME_BRONZE, TABLE_NAME
from extract import extrair_dados_bronze
from load import carregar_dados
from transform import transformar_dados
from logger_config import setup_logger

# ============================================================================
# Pipeline Final
# ============================================================================
setup_logger()
logger = logger


@logger.catch
def main():
    """
    Função principal do pipeline.
    1. Extrai os dados CSV da pasta bronze.
    2. Registra um resumo da extração.
    3. Transforma os dados extraídos.
    4. Carrega os dados transformados no MariaDB.
    """
    # ===========================================================================
    # Etapa de extração de dados
    # ===========================================================================
    try:
        logger.info("Iniciando pipeline...")
        df = extrair_dados_bronze(DATA_BRONZE_PATH)
        if df is None or df.empty:
            logger.warning("Nenhum dado extraído.")
        else:
            logger.info(f"Dados extraídos: {len(df)} linhas x {len(df.columns)} colunas")
    except Exception as e:
        logger.error(f"Erro no pipeline: {e}")
        sys.exit(1)
    # ===========================================================================
    # Etapa de transformação de dados
    # ===========================================================================
    try:
        if df is None or df.empty:
            logger.warning("Pipeline interrompido: não há dados para transformar")
            return
        df = transformar_dados(df)
        logger.info(f"Dados transformados: {len(df)} linhas x {len(df.columns)} colunas")
    except Exception as e:
        logger.error(f"Erro na transformação de dados: {e}")
        sys.exit(1)
    # ===========================================================================
    # Etapa de carregamento de dados
    # ===========================================================================
    try:
        total = carregar_dados(
            df,
            tabela=TABLE_NAME,
            schema=SCHEMA_NAME_BRONZE,
        )
        logger.info(f"Dados carregados no MotherDuck: {total} linhas")
    except Exception as e:
        logger.error(f"Erro no carregamento do MotherDuck: {e}")
        sys.exit(1)
    logger.info("Pipeline concluído com sucesso.")
if __name__ == "__main__":
    main()

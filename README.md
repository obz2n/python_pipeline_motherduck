# Python Pipeline com MotherDuck

![img](https://i.postimg.cc/DZ50XLds/motherduck.png)

Pipeline de dados **end-to-end** (ETL) que extrai dados de campanhas do Google Ads, transforma-os e os carrega no [MotherDuck](https://motherduck.com/) (DuckDB na nuvem), com visualização em um dashboard Streamlit e automação diária via GitHub Actions.

## Visão geral da arquitetura

```
CSV (bronze) --> Extract --> Transform --> Load (MotherDuck) --> Dashboard (Streamlit)
```

- **Extração** (`src/extract.py`): lê o CSV de origem detectando automaticamente encoding e separador.
- **Transformação** (`src/transform.py`): limpeza e padronização dos dados extraídos.
- **Carga** (`src/load.py`): grava os dados transformados em uma tabela no MotherDuck.
- **Orquestração** (`src/main.py`): executa as três etapas em sequência, com logs estruturados (`loguru`).
- **Visualização** (`app/main.py`): dashboard Streamlit para explorar os dados carregados.
- **Automação** (`.github/workflows/main.yml`): executa o pipeline e o dashboard diariamente via GitHub Actions (cron), ou manualmente (`workflow_dispatch`).

## Estrutura do projeto

```
python_pipeline_motherduck/
├── app/            # Dashboard Streamlit
├── data/           # Dados de origem (camada bronze)
├── docs/           # Documentação adicional
├── logs/           # Logs gerados pela execução do pipeline
├── src/            # Código-fonte do pipeline (extract, transform, load)
├── tests/          # Testes automatizados
└── .github/        # Workflows de CI/CD (GitHub Actions)
```

## Pré-requisitos

- Python 3.12+
- Conta no [MotherDuck](https://motherduck.com/) com um token de acesso

## Instalação

```bash
git clone <url-do-repositorio>
cd python_pipeline_motherduck
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com o token do MotherDuck:

```env
NAME='nome-do-token'
MOTHERDUCK_TOKEN='seu-token-aqui'
```

## Como executar

Executar o pipeline (extração, transformação e carga):

```bash
python src/main.py
```

Executar o dashboard Streamlit:

```bash
streamlit run app/main.py
```

## Automação (CI/CD)

O workflow [.github/workflows/main.yml](.github/workflows/main.yml) executa o pipeline automaticamente todos os dias às 07:00 (horário de Brasília) e pode ser disparado manualmente pela aba **Actions** do repositório. É necessário configurar o secret `MOTHERDUCK_TOKEN` (e, opcionalmente, `PREFECT_API_KEY`/`PREFECT_API_URL`) em **Settings > Secrets and variables > Actions**.


## Obs
Crie o banco diretamente no MotherDuck caso apresente algum erro na etapa de carregamento

## Autor

[Juliano Laurentino](https://www.linkedin.com/in/julianolaurentinodasilva/)

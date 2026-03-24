# 🦟 Pipeline de Arboviroses Brasil — Arquitetura Medallion

> Plataforma de engenharia de dados para análise epidemiológica de **Dengue**, **Zika** e **Chikungunya** no Brasil (2020–2024), construída sobre **Apache Spark** e **Delta Lake** com arquitetura Medallion no **Databricks Free Edition**, armazenamento em **AWS S3 (Free Tier)**.

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Ambiente de Desenvolvimento](#ambiente-de-desenvolvimento)
- [Arquitetura](#arquitetura)
- [Fontes de Dados](#fontes-de-dados)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Camadas da Arquitetura Medallion](#camadas-da-arquitetura-medallion)
- [Cronograma de Desenvolvimento](#cronograma-de-desenvolvimento)
- [Entregáveis](#entregáveis)
- [Próximos Passos](#próximos-passos)
- [Referências](#referências)

---

## Visão Geral

As arboviroses transmitidas pelo *Aedes aegypti* representam um dos maiores desafios de saúde pública do Brasil. Este projeto constrói um **pipeline de dados end-to-end** para consolidar, limpar e analisar os dados de notificação do SINAN/DATASUS, enriquecendo-os com informações demográficas do IBGE e dados climáticos do INMET.

**Objetivos principais:**

- Ingerir microdados públicos do SINAN de três doenças com estratégias de extração distintas: **CSV** (Dengue), **API REST** (Zika) e **XML** (Chikungunya)
- Converter e persistir todos os dados em **Delta Table** no **AWS S3**, usando `s3a://` como protocolo de acesso
- Aplicar a **arquitetura Medallion** (Bronze → Silver → Gold) com Delta Lake e Hive Metastore
- Produzir métricas epidemiológicas: taxa de incidência por município, sazonalidade e correlação clima × casos
- Demonstrar boas práticas de engenharia de dados dentro das restrições de um ambiente gratuito: qualidade de dados, testes automatizados e documentação

---

## Ambiente de Desenvolvimento

Este projeto foi desenvolvido intencionalmente com ferramentas **100% gratuitas**, tornando-o acessível e reproduzível por qualquer pessoa.

| Serviço | Plano | Limitações relevantes |
|---|---|---|
| **Databricks Community Edition** | Gratuito | Cluster single-node, sem Workflows, sem Unity Catalog, sem Auto Loader com SQS |
| **AWS S3** | Free Tier (12 meses) | 5 GB armazenamento, 20k GET, 2k PUT/mês |
| **AWS IAM** | Sempre gratuito | Usuário com Access Key + Secret Key |
| **GitHub** | Gratuito | Repositório público + Databricks Repos |

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FONTES DE DADOS                              │
│  SINAN/DATASUS (ZIP→CSV)   │  OpenDengue API (REST)  │  SINAN (XML) │
│         Dengue             │          Zika            │  Chikungunya │
└──────────┬─────────────────┴──────────┬───────────────┴──────┬───────┘
           │                            │                       │
           └────────────────────────────┴───────────────────────┘
                                        │  boto3 upload
                             ┌──────────▼───────────────────┐
                             │         AWS S3               │
                             │  s3a://bucket/bronze/        │
                             │        landing/              │
                             └──────────┬───────────────────┘
                                        │  spark.read (batch)
                             ┌──────────▼──────────┐
                             │   🥉 BRONZE LAYER    │
                             │  Delta Tables Raw    │
                             │  StringType — tudo   │
                             │  + metadados audit.  │
                             └──────────┬──────────┘
                                        │  PySpark Transformations
                             ┌──────────▼──────────┐
                             │   🥈 SILVER LAYER    │
                             │  Tipagem + Dedup     │
                             │  + Join IBGE         │
                             │  + Semana Epidem.    │
                             └──────────┬──────────┘
                                        │  Agregações & Métricas
                             ┌──────────▼──────────┐
                             │   🥇 GOLD LAYER      │
                             │  Incidência/100k     │
                             │  Série Temporal      │
                             │  Correlação Clima    │
                             └──────────┬──────────┘
                                        │
                   ┌────────────────────┴────────────────────┐
                   │                                         │
        ┌──────────▼──────────┐                  ┌──────────▼──────────┐
        │  Notebooks Análise  │                  │  Visualizações      │
        │  (Databricks CE)    │                  │  Matplotlib/Plotly  │
        └─────────────────────┘                  └─────────────────────┘
```

### Estrutura do bucket S3

```
s3://arbovirose-portfolio-dev/
├── bronze/
│   ├── dengue/
│   │   ├── landing/          ← CSVs brutos extraídos do ZIP
│   │   └── delta/            ← Delta Table física (Parquet + _delta_log)
│   ├── zika/
│   │   ├── landing/
│   │   └── delta/
│   └── chikungunya/
│       ├── landing/
│       └── delta/
├── silver/
│   └── arbovirose_enriquecida/   ← particionado por ANO_NOTIFIC/SG_UF
├── gold/
│   ├── incidencia_municipio_semana/
│   ├── serie_temporal_uf/
│   └── correlacao_clima_casos/
└── reference/
    ├── municipios_ibge.csv
    └── codigos_cid10.csv
```

---

## Fontes de Dados

| Doença | Formato | Fonte | URL |
|---|---|---|---|
| 🦟 **Dengue** | ZIP → **CSV** | SINAN / DATASUS | `s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBRxx.csv.zip` |
| 🦠 **Zika** | **ZIP** (JSON) | SINAN / DATASUS | `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Chikungunya/json/CHIKBRxx.json.zip` |
| 🦗 **Chikungunya** | **ZIP** (XML) | SINAN / DATASUS | `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Chikungunya/xml/CHIKBRxx.xml.zip` |
| 🗺 **Municípios** | **API REST** (JSON) | IBGE | `servicodados.ibge.gov.br/api/v1/localidades/municipios` |
| 🌧 **Clima** | CSV | INMET BDMEP | `bdmep.inmet.gov.br` |

**Período coberto:** 2020 – 2025 (6 anos de dados, sufixos `20` a `25` no nome do arquivo)

---

## Estrutura do Projeto

```
arbovirose-pipeline/
│
├── notebooks/
│   ├── 00_setup_ambiente.py            # Configura S3, cria schemas, testa conexão
│   ├── bronze/
│   │   ├── 01_ingestao_dengue_csv.py   # Download ZIP → CSV → Delta (s3a)
│   │   ├── 02_ingestao_zika_api.py     # Download ZIP → JSON → Delta
│   │   └── 03_ingestao_chikungunya.py  # Download ZIP → XML → Delta
│   ├── silver/
│   │   ├── 04_limpeza_dedup.py         # Dedup + tipagem + nulos
│   │   ├── 05_enriquecimento_ibge.py   # Join IBGE + semana epidemiológica
│   │   └── 06_join_clima_inmet.py      # Join dados climáticos
│   ├── gold/
│   │   ├── 07_incidencia_municipio.py  # Taxa por município e semana
│   │   ├── 08_serie_temporal_uf.py     # Evolução mensal por UF
│   │   └── 09_correlacao_clima.py      # Pearson clima × casos + lag
│   └── analytics/
│       └── 10_visualizacoes.py         # Gráficos exploratórios (matplotlib/plotly)
│
├── utils/
│   ├── s3_config.py            # Configuração s3a + credenciais via env vars
│   ├── schema_definitions.py   # Schemas explícitos por doença
│   ├── date_utils.py           # Semana epidemiológica BR
│   └── geo_utils.py            # Haversine, join geoespacial
│
├── tests/
│   ├── test_bronze_schemas.py
│   ├── test_silver_quality.py
│   └── test_gold_metrics.py
│
├── data/
│   └── reference/
│       ├── municipios_ibge.csv
│       └── codigos_cid10.csv
│
├── docs/
│   ├── dicionario_dados_dengue.md       # Dicionário de variáveis SINAN
│   └── dicionario_dados_zika.md       # Dicionário de variáveis SINAN
│   └── dicionario_dados_chikungunya.md       # Dicionário de variáveis SINAN
│
├── .gitignore                    # Exclui credenciais e dados brutos
├── requirements.txt
└── README.md
```
---

## Tecnologias Utilizadas

| Categoria | Tecnologia | Detalhe |
|---|---|---|
| Plataforma | **Databricks Free Edition** | Runtime 14.3 LTS (Spark 3.5, Python 3.10) — gratuito |
| Cloud Storage | **AWS S3 Free Tier** | Bucket `sa-east-1`, protocolo `s3a://` via Hadoop |
| Autenticação AWS | **IAM User + Access Key** | Credenciais em variáveis de ambiente do cluster |
| Upload S3 | **boto3** | Upload de arquivos brutos para landing zone |
| Processamento | **Apache Spark / PySpark** | 3.5 — DataFrame API, Window Functions |
| Armazenamento | **Delta Lake** | ACID, time travel, schema evolution |
| Metastore | **Hive Metastore** | Schemas bronze / silver / gold (sem Unity Catalog) |
| Qualidade | **Great Expectations** | Validação de schemas e dados por camada |
| Testes | **pytest + chispa** | Testes unitários para transformações PySpark |
| Versionamento | **Git + Databricks Repos** | Notebooks versionados via GitHub |
| Visualização | **Matplotlib / Plotly** | Gráficos nos notebooks analíticos |
| Formato físico | **Parquet / Delta Table** | Particionamento por ano e UF |
| Bibliotecas extras | `pyreaddbc`, `spark-xml`, `httpx`, `scipy`, `boto3` | Ver `requirements.txt` |

---

## Camadas da Arquitetura Medallion

### 🥉 Bronze — Ingestão Bruta

Recebe os dados **exatamente como vieram da fonte**, sem nenhuma transformação de negócio. O CSV extraído do ZIP é salvo primeiro na landing zone do S3 via `boto3`, depois lido pelo Spark com `inferSchema=false` — tudo como `StringType`. Cada tabela recebe colunas de metadado (`_fonte`, `_data_ingestao`, `_ano_referencia`, `_formato_origem`) para rastreabilidade total. Gravação append-only com `mergeSchema=true` para suportar eventuais variações entre arquivos de anos diferentes.

**Tabelas:** `bronze.dengue_raw` · `bronze.zika_raw` · `bronze.chikungunya_raw`

---

### 🥈 Silver — Limpeza e Enriquecimento

Aplica deduplicação por `NU_NOTIFIC + CO_MUN_NOT` com Window Functions, converte tipos (datas de `yyyyMMdd` para `DateType`, idades do formato codificado SINAN para `IntegerType`, padronização de sexo e códigos IBGE com zero-padding), calcula a semana epidemiológica brasileira via UDF e enriquece com join na API do IBGE (nome do município, UF, região) e dados climáticos do INMET (temperatura e precipitação mensal). Tabelas particionadas por `ANO_NOTIFIC` e `SG_UF`.

**Tabelas:** `silver.arbovirose_cleaned` · `silver.arbovirose_enriquecida` · `silver.clima_municipio`

---

### 🥇 Gold — Camada Analítica

Contém tabelas pré-agregadas prontas para consumo analítico. Entrega taxa de incidência por 100k habitantes por município e semana epidemiológica, série temporal mensal por UF com baseline histórico (2020–2023 vs anos seguintes) e correlação de Pearson entre precipitação/temperatura e incidência testando lag de 2 a 4 semanas (hipótese do ciclo biológico do *Aedes aegypti*).

**Tabelas:** `gold.incidencia_municipio_semana` · `gold.serie_temporal_uf` · `gold.correlacao_clima_casos`

---

## Cronograma de Desenvolvimento

### Infraestrutura + Camada Bronze

| Checkpoint | Fase | Atividade | Tecnologias |
|---|---|---|---|
| ❌ | Infra | Criar conta Databricks CE e AWS Free Tier. Criar bucket S3 (`sa-east-1`), usuário IAM com policy restrita ao bucket, Access Key. Configurar cluster com variáveis de ambiente AWS. Criar schemas `bronze`/`silver`/`gold` via Hive Metastore. Conectar Databricks Repos ao GitHub | Databricks CE · AWS S3 · IAM · Git · Hive Metastore |
| ⏳ | Bronze |Baixar dados Dengue (CSV), enviar para o S3, ler com PySpark e gravar `bronze.dengue` em Delta Lake particionada por `_ano_referencia`| `requests` · `boto3` · PySpark · Delta Lake · `s3a://` |
| ⏳ | Bronze | Baixar dados Zika (JSON), enviar para o S3, ler com PySpark e gravar `bronze.zika` em Delta Lake particionada por `_ano_referencia` | `requests` · `boto3` · PySpark · Delta Lake · `s3a://` |
| ⏳| Bronze | Baixar dados Chikungunya (XML), enviar para o S3, ler com PySpark e gravar `bronze.chikungunya` em Delta Lake particionada por `_ano_referencia`| `requests` · `boto3` · PySpark · Delta Lake · `s3a://` |
|  | Bronze | Validar schemas das 3 tabelas com Great Expectations (nullability, tipos, ranges de data). Notebook de auditoria: contagem de registros por ano e fonte. Documentar dicionário de dados SINAN | Great Expectations · PySpark |

---

### Silver, Gold, Testes e Entregáveis

| Checkpoint | Fase | Atividade | Tecnologias |
|---|---|---|---|
|  | Silver | Deduplicação por `NU_NOTIFIC + CO_MUN_NOT` com Window Functions. Tratamento de nulos críticos (`DT_SIN_PRI`, `CO_MUN_NOT`). Cast de tipos: datas, idades (formato SINAN), sexo, códigos IBGE com zero-padding → `silver.arbovirose_cleaned` | PySpark · Window Functions · Delta Lake |
|  | Silver | Join com API IBGE (nome município, UF, região). Cálculo da semana epidemiológica BR via UDF. Gravar `silver.arbovirose_enriquecida` particionada por `ANO_NOTIFIC`/`SG_UF` | PySpark Joins · API IBGE · UDF Python |
|  | Silver | Ingerir dados climáticos INMET (temperatura e precipitação mensais). Join com municípios por proximidade (haversine) → `silver.clima_municipio` | PySpark · `scipy` · haversine |
|  | Gold | `gold.incidencia_municipio_semana`: taxa por 100k habitantes. `gold.serie_temporal_uf`: evolução mensal com baseline histórico | PySpark `groupBy`/`agg` · Delta Lake |
|  | Gold | `gold.correlacao_clima_casos`: Pearson precipitação/temperatura × incidência com lag 2–4 semanas. Visualizações exploratórias nos notebooks | `scipy.stats` · Pandas UDF · Plotly |
|  | Testes | Testes unitários com `pytest + chispa` para transformações Silver. Suite Great Expectations por camada. Validar contagens, ranges de datas e taxa de nulos | pytest · chispa · Great Expectations |
| | Portfólio | README técnico final, exportar notebooks em HTML, gravar demo em vídeo (Loom), publicar no GitHub, atualizar LinkedIn com descrição do projeto | GitHub · Markdown · Loom |

---

## Entregáveis

- [ ] 3 tabelas Bronze em Delta Lake no S3 (uma por doença, com metadados de auditoria)
- [ ] 3 tabelas Silver (limpeza + tipagem, enriquecimento IBGE, dados climáticos)
- [ ] 3 tabelas Gold (incidência/100k, série temporal, correlação clima × casos)
- [ ] Visualizações analíticas nos notebooks (Matplotlib/Plotly)
- [ ] Suite de testes com pytest + chispa + Great Expectations
- [ ] Dicionário de dados das variáveis SINAN documentado
- [ ] Repositório público no GitHub com README e diagrama de arquitetura
- [ ] Dashboard interativo *(limitação da Community Edition — previsto para versão produção)*
- [ ] Orquestração via Workflows *(limitação da Community Edition — previsto para versão produção)*
- [ ] Modelo preditivo de surtos com MLflow + Spark MLlib *(próxima fase)*

---

## Próximos Passos

1. **Migração para ambiente de produção** — replicar o pipeline em um Databricks E2 Workspace com IAM Role via Instance Profile, Unity Catalog com External Location no S3 e Databricks Workflows para orquestração — sem alterar nenhuma linha das transformações PySpark
2. **Modelo preditivo** — usar features de clima e sazonalidade para prever surtos com MLflow + Spark MLlib, registrando experimentos no Model Registry
3. **Delta Live Tables** — reescrever o pipeline usando DLT para qualidade declarativa e lineage automático
4. **Streaming em tempo real** — migrar ingestão para Structured Streaming com alertas quando a taxa de incidência ultrapassa limiar configurável
5. **Expansão de fontes** — incluir dados de infestação do *Aedes aegypti* (LIRAa/PNCD) e cobertura de saneamento básico (SNIS)

---

## Referências

- [DATASUS / SINAN — Microdados de Arboviroses](https://datasus.saude.gov.br/transferencia-de-arquivos/)
- [SINAN Dengue — Arquivos CSV públicos (S3)](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/)
- [OpenDengue — Dataset Global de Dengue e Arboviroses](https://opendengue.org)
- [IBGE — API de Localidades e População](https://servicodados.ibge.gov.br/api/docs/localidades)
- [INMET BDMEP — Banco de Dados Meteorológicos](https://bdmep.inmet.gov.br)
- [Databricks Community Edition](https://community.cloud.databricks.com)
- [Delta Lake — Documentação](https://docs.databricks.com/delta/index.html)
- [Apache Spark PySpark API](https://spark.apache.org/docs/latest/api/python/)
- [Great Expectations — Documentação](https://docs.greatexpectations.io)
- [pyreaddbc — Leitor de arquivos .dbc](https://github.com/AlertaDengue/pyreaddbc)
- [spark-xml — Leitor XML para Spark](https://github.com/databricks/spark-xml)
- [boto3 — AWS SDK para Python](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

*Projeto desenvolvido como portfólio de engenharia de dados utilizando exclusivamente ferramentas gratuitas (Databricks Community Edition + AWS Free Tier). Dados utilizados são públicos e de domínio governamental brasileiro.*
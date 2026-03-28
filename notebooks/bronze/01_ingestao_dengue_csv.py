"""
ingestao_bronze_dengue.py
=========================
Camada Bronze — Ingestão dos microdados de Dengue (SINAN/DATASUS)
Fonte : https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBRxx.csv.zip
Fluxo : download ZIP → extração CSV em memória → leitura PySpark → gravação Delta Table no S3

"""

import os
import requests
import zipfile
from pyspark.sql import SparkSession

ANOS = [
    "20", "21"
    # "22", "23", "24", "25"
]

BASE_PATH = "./data/bronze/dengue"

LANDING_BASE_PATH = f"{BASE_PATH}/landing"
DELTA_PATH = f"{BASE_PATH}/delta"

os.makedirs(LANDING_BASE_PATH, exist_ok=True)
os.makedirs(DELTA_PATH, exist_ok=True)


spark = SparkSession.builder \
    .appName("dengue-bronze-local") \
    .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()


for ano in ANOS:
    YEAR = f"20{ano}"
    FILE_ID = f"DENGBR{ano}"
    URL = f"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/{FILE_ID}.csv.zip"

    LANDING_YEAR_PATH = f"{LANDING_BASE_PATH}/{YEAR}"
    os.makedirs(LANDING_YEAR_PATH, exist_ok=True)
    RAW_ZIP_PATH = f"{LANDING_YEAR_PATH}/{FILE_ID}.zip"

    print(f"\n==============================================")
    print(f"Iniciando ingestão do ano: {YEAR}")
    print(f"Baixando: {URL}")

    try:
        response = requests.get(URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao baixar {URL}: {e}")
        continue

    with open(RAW_ZIP_PATH, "wb") as f:
        f.write(response.content)

    print("Download concluído")

    with zipfile.ZipFile(RAW_ZIP_PATH, "r") as z:
        z.extractall(LANDING_YEAR_PATH)
        csv_file = [f for f in z.namelist() if f.endswith(".csv")][0]

    CSV_PATH = os.path.join(LANDING_YEAR_PATH, csv_file)

    print(f"CSV salvo em: {CSV_PATH}")

    from pyspark.sql.functions import lit

    df = spark.read \
        .option("header", True) \
        .option("inferSchema", False) \
        .option("sep", ",") \
        .option("encoding", "iso-8859-1") \
        .option("mode", "PERMISSIVE") \
        .csv(CSV_PATH) \
        .withColumn("ano", lit(YEAR))

    print(f"Schema do ano {YEAR}:")
    df.printSchema()

    df.write \
        .format("delta") \
        .mode("append") \
        .partitionBy("ano") \
        .option("mergeSchema", "true") \
        .save(DELTA_PATH)

    print(f"Dados do ano {YEAR} salvos em Delta (partição ano={YEAR}): {DELTA_PATH}")

print("\n==============================================")
print("Ingestão completa de todos os anos disponíveis.")
df_delta = spark.read.format("delta").load(DELTA_PATH)

print("Validação (Delta):")
df_delta.show(5, truncate=False)
print(f"Total de registros na tabela Delta: {df_delta.count()}")

spark.stop()
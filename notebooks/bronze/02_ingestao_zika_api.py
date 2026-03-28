"""
ingestao_bronze_zika.py
=========================
Camada Bronze — Ingestão dos microdados de Zika (SINAN/DATASUS)
Fonte : https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Zikavirus/json/ZIKABRxx.json.zip
Fluxo : download ZIP → extração JSON em memória → leitura PySpark → gravação Delta Table no S3

"""

import os
import requests
import zipfile
from pyspark.sql import SparkSession

from pyspark.sql.functions import col, lit

ANOS = [
    "20",
    # "21","22", "23", "24", "25"
]


BASE_PATH = "./data/bronze/zika"

LANDING_BASE_PATH = f"{BASE_PATH}/landing"
DELTA_PATH = f"{BASE_PATH}/delta"


os.makedirs(LANDING_BASE_PATH, exist_ok=True)
os.makedirs(DELTA_PATH, exist_ok=True)


spark = SparkSession.builder \
    .appName("zika-bronze-local") \
    .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()


for ano in ANOS:
    YEAR = f"20{ano}"
    FILE_ID = f"ZIKABR{ano}"
    URL = f"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Zikavirus/json/{FILE_ID}.json.zip"

    # Particionamento da landing por ano: landing/2020/ZIKABR20.zip
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
        json_file = [f for f in z.namelist() if f.endswith(".json")][0]

    JSON_PATH = os.path.join(LANDING_YEAR_PATH, json_file)

    print(f"JSON salvo em: {JSON_PATH}")

    df = spark.read \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", True) \
        .json(JSON_PATH) \
        .withColumn("ano", lit(YEAR)) \
        .cache()

    print(f"Schema do ano {YEAR}:")
    df.printSchema()

    if "_corrupt_record" in df.columns:
        df_valid = df.filter(col("_corrupt_record").isNull())
        df_invalid = df.filter(col("_corrupt_record").isNotNull())

        invalid_count = df_invalid.count()
        if invalid_count > 0:
            print(f"ATENÇÃO: {invalid_count} Registros corrompidos no ano 20{ano}:")
            df_invalid.show(5, truncate=False)
    else:
        df_valid = df

    if "_corrupt_record" in df_valid.columns:
        df_valid = df_valid.drop("_corrupt_record")

    df_valid.write \
        .format("delta") \
        .mode("append") \
        .partitionBy("ano") \
        .option("mergeSchema", "true") \
        .save(DELTA_PATH)

    print(f"Dados do ano {YEAR} salvos em Delta (partição ano={YEAR}): {DELTA_PATH}")
    
    df.unpersist()

print("\n==============================================")
print("Ingestão completa de todos os anos disponíveis.")
df_delta = spark.read.format("delta").load(DELTA_PATH)

print("Validação (Delta):")
df_delta.show(5, truncate=False)
print(f"Total de registros na tabela Delta: {df_delta.count()}")

spark.stop()
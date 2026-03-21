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

ANO = "23"

FILE_ID = f"DENGBR{ANO}"
URL = f"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/{FILE_ID}.csv.zip"

BASE_PATH = "./data/bronze/dengue"

LANDING_PATH = f"{BASE_PATH}/landing"
DELTA_PATH = f"{BASE_PATH}/delta"

RAW_ZIP_PATH = f"{LANDING_PATH}/{FILE_ID}.zip"


os.makedirs(LANDING_PATH, exist_ok=True)
os.makedirs(DELTA_PATH, exist_ok=True)


spark = SparkSession.builder \
    .appName("dengue-bronze-local") \
    .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()


print(f"Baixando: {URL}")

response = requests.get(URL)
response.raise_for_status()

with open(RAW_ZIP_PATH, "wb") as f:
    f.write(response.content)

print("Download concluído")

with zipfile.ZipFile(RAW_ZIP_PATH, "r") as z:
    z.extractall(LANDING_PATH)
    csv_file = [f for f in z.namelist() if f.endswith(".csv")][0]

CSV_PATH = os.path.join(LANDING_PATH, csv_file)

print(f"CSV salvo em: {CSV_PATH}")

df = spark.read \
    .option("header", True) \
    .option("inferSchema", False) \
    .option("sep", ",") \
    .option("encoding", "iso-8859-1") \
    .option("mode", "PERMISSIVE") \
    .csv(CSV_PATH)

print("Schema:")
df.printSchema()

print("Preview:")
df.show(5, truncate=False)

df.write \
    .format("delta") \
    .mode("append") \
    .save(DELTA_PATH)

print(f"Dados salvos em Delta: {DELTA_PATH}")

df_delta = spark.read.format("delta").load(DELTA_PATH)

print("Validação (Delta):")
df_delta.show(5, truncate=False)

spark.stop()
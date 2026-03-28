"""
ingestao_bronze_chikungunya.py
=========================
Camada Bronze — Ingestão dos microdados de Chikungunya (SINAN/DATASUS)
Fonte : https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBRxx.csv.zip
Fluxo : download ZIP → extração XML em memória → leitura PySpark → gravação Delta Table no S3

"""

import os
import requests
import zipfile
import xml.etree.ElementTree as ET
from pyspark.sql import SparkSession
from pyspark.sql.functions import lit

ANOS = [
    "20",
    # "21","22", "23", "24", "25"
]

BASE_PATH = "./data/bronze/chikungunya"

LANDING_BASE_PATH = f"{BASE_PATH}/landing"
DELTA_PATH = f"{BASE_PATH}/delta"


os.makedirs(LANDING_BASE_PATH, exist_ok=True)
os.makedirs(DELTA_PATH, exist_ok=True)


spark = SparkSession.builder \
    .appName("chikungunya-bronze-local") \
    .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0,com.databricks:spark-xml_2.12:0.18.0") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.sql.parquet.datetimeRebaseModeInWrite", "LEGACY") \
    .getOrCreate()


for ano in ANOS:
    YEAR = f"20{ano}"
    FILE_ID = f"CHIKBR{ano}"
    URL = f"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Chikungunya/xml/{FILE_ID}.xml.zip"

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
        xml_file = [f for f in z.namelist() if f.endswith(".xml")][0]

    XML_PATH = os.path.join(LANDING_YEAR_PATH, xml_file)

    print(f"XML extraído em: {XML_PATH}")
    print("Mapeando estrutura (Schema/Tag) usando streaming com ElementTree...")

    row_tag = None
    try:
        context = ET.iterparse(XML_PATH, events=("start",))
        _, root = next(context)
        
        for event, elem in context:
            if event == "start" and elem != root:
                row_tag = elem.tag
                break
    except Exception as e:
        pass

    if not row_tag:
        row_tag = "Linha"

    print(f"Tag de linha definida dinamicamente como: <{row_tag}>")

    df = spark.read \
        .format("xml") \
        .option("rowTag", row_tag) \
        .option("inferSchema", True) \
        .option("encoding", "iso-8859-1") \
        .option("mode", "DROPMALFORMED") \
        .load(XML_PATH) \
        .withColumn("ano", lit(YEAR)) \
        .cache()

    row_count = df.count()
    if row_count > 0:
        print(f"Schema final mapeado pelo Spark (Ano {YEAR}):")
        df.printSchema()

        df.write \
            .format("delta") \
            .mode("append") \
            .partitionBy("ano") \
            .option("mergeSchema", "true") \
            .save(DELTA_PATH)

        print(f"Sucesso: {row_count} dados do ano {YEAR} salvos em Delta (partição ano={YEAR}): {DELTA_PATH}")
    else:
        print(f"ATENÇÃO: Nenhum dado capturado usando a tag <{row_tag}> para o ano {YEAR}.")

    df.unpersist()

print("\n==============================================")
print("Ingestão completa de todos os anos disponíveis.")
df_delta = spark.read.format("delta").load(DELTA_PATH)

print("Validação final (Delta):")
df_delta.show(5, truncate=False)
print(f"Total de registros consolidados na camada Bronze (Delta): {df_delta.count()}")

spark.stop()
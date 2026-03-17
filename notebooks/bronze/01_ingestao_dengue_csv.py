"""
ingestao_bronze_dengue.py
=========================
Camada Bronze — Ingestão dos microdados de Dengue (SINAN/DATASUS)
Fonte : https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBRxx.csv.zip
Fluxo : download ZIP → extração CSV em memória → leitura PySpark → gravação Delta Table no S3

"""

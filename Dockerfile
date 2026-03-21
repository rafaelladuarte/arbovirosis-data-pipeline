FROM jupyter/pyspark-notebook:latest

WORKDIR /home/jovyan/work

COPY requirements.txt .

USER root
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

USER jovyan

CMD ["start-notebook.sh", "--NotebookApp.token=''"]
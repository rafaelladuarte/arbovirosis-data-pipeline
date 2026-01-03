# 🦟 Arboviroses Data Pipeline – Brasil

## Visão Geral
Este projeto consiste no desenvolvimento de um **pipeline de dados para análise de arboviroses no Brasil**, criado como **projeto final do curso Data Engineering Zoomcamp**, promovido pela comunidade **DataTalksClub**  
(https://github.com/DataTalksClub/data-engineering-zoomcamp).

## Fonte de Dados
A pipeline utiliza como principal fonte a **API de Dados Abertos do Ministério da Saúde**:  
https://apidadosabertos.saude.gov.br/v1/  
Inicialmente, o foco será a **coleta e o processamento de dados de Dengue**, com expansão planejada para **Zika e Chikungunya** em etapas posteriores do projeto.

## Enriquecimento de Dados
Os dados epidemiológicos coletados serão **enriquecidos com informações geográficas e administrativas do IBGE**, como município, unidade federativa e região, possibilitando análises territoriais mais completas e visualizações analíticas mais consistentes.

## Arquitetura e Organização da Pipeline
A **arquitetura e o stack tecnológico ainda estão em fase de definição**. No entanto, o projeto seguirá, a princípio, uma organização baseada em **camadas Bronze, Prata e Ouro**, contemplando:
- Extração e ingestão de dados brutos (Bronze)
- Tratamento, padronização e enriquecimento dos dados (Prata)
- Modelagem analítica e disponibilização para consumo (Ouro)

## Objetivo do Projeto
O objetivo principal é **aplicar boas práticas de engenharia de dados**, incluindo ingestão de dados públicos, processamento analítico, enriquecimento de informações e **disponibilização dos dados para análise e visualização em dashboards**, simulando um cenário real de dados epidemiológicos em larga escala.

# MaisPB Web Scraper

Este é um script de web scraping em Python desenvolvido para extrair as principais notícias da página inicial do portal [MaisPB](https://www.maispb.com.br).

O script utiliza bibliotecas open source e leves, não dependendo de navegadores.

## Dados Extraídos

O script acessa a página inicial do site e extrai os seguintes dados para cada notícia encontrada:
- **Título da notícia**
- **Link (URL original da notícia)**
- **Imagem de destaque** (Lidando com lazy loading para capturar o link real da imagem)

Os resultados são salvos em um arquivo local `noticias.json` contendo um array estruturado.

## Pré-requisitos

É necessário possuir o Python 3 instalado no sistema.

## Instalação

1. Clone o repositório ou acesse a pasta `maispb`:
   ```bash
   cd maispb
   ```

2. Instale as dependências. É recomendável o uso de um ambiente virtual (venv). Instale os pacotes através do pip:
   ```bash
   pip install requests beautifulsoup4
   ```

## Como Executar

Para rodar o script e extrair as notícias, execute:

```bash
python3 scraper.py
```

O script irá criar (ou sobrescrever) o arquivo `noticias.json` no mesmo diretório com os dados extraídos.

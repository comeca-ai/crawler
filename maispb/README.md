# MaisPB Scraper

Este é um script de web scraping para extrair as principais notícias do portal MaisPB (www.maispb.com.br).

## Funcionalidades
- Extrai títulos, links e imagens das notícias da página inicial
- Identifica padrões de URL únicos para evitar duplicações e capturar apenas artigos de notícias
- Salva os dados de forma estruturada e organizada em um arquivo JSON

## Requisitos
- Python 3.x
- `requests`
- `beautifulsoup4`

## Instalação

```bash
pip install requests beautifulsoup4
```

## Como usar

Execute o script `scraper.py`:

```bash
python3 scraper.py
```

O script fará o download da página, analisará as notícias e criará um arquivo `noticias.json` na mesma pasta com os resultados organizados.

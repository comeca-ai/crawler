# Paraíba Online Scraper

Este é um script de web scraping para extrair as principais notícias do site Paraíba Online (paraibaonline.com.br).

## Funcionalidades
- Extrai títulos, links e imagens das notícias da página inicial
- Trata lazy loading de imagens e background images (CSS inline) para capturar a arte do post
- Salva os dados de forma estruturada e organizada em um arquivo JSON

## Requisitos
- Python 3.x
- `requests`
- `beautifulsoup4`

## Instalação

```bash
pip install -r ../requirements.txt
```
*(Ou `pip install requests beautifulsoup4`)*

## Como usar

Execute o script `scraper.py`:

```bash
python3 scraper.py
```

O script fará o download da página, analisará as notícias e criará um arquivo `noticias.json` na mesma pasta com os resultados organizados.

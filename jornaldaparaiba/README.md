# Jornal da Paraíba Scraper

Este é um script de web scraping para extrair as principais notícias do portal Jornal da Paraíba (www.jornaldaparaiba.com.br).

## Funcionalidades
- Extrai títulos, links e imagens das notícias da página inicial
- Trata URLs de imagens para pegar as fontes originais e em melhor qualidade
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

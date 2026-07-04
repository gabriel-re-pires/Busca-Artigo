# Busca-Artigo

[![Release](https://img.shields.io/github/v/release/gabriel-re-pires/Busca-Artigo)](https://github.com/gabriel-re-pires/Busca-Artigo/releases/latest)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-blue)
![Python](https://img.shields.io/badge/python-3.x-yellow)

Aplicação desktop para busca e ranqueamento de artigos científicos, desenvolvida como apoio à pesquisa acadêmica de TCC.

---

## Download

> Apenas para Windows — não requer Python, editor de código ou qualquer instalação adicional.

**[⬇️ Baixar Busca-Artigo v1.2.0](https://github.com/gabriel-re-pires/Busca-Artigo/releases/download/v1.2.0/Busca-Artigo_v1.2.0.zip)**

Após baixar, extraia o `.zip` e execute `Busca-Artigo.exe`.

---

## O que faz

O Busca-Artigo pesquisa artigos simultaneamente em três bases acadêmicas — **arXiv**, **Google Scholar** e **Semantic Scholar** — e apresenta os resultados ordenados por relevância. A ordenação usa um algoritmo de pontuação composta que considera:

- Similaridade semântica com o tema pesquisado (40%)
- Número de citações (25%)
- Recência da publicação (20%)
- Correspondência de palavras-chave no título (10%)
- Qualidade do resumo (5%)

Os resultados podem ser exportados em **Excel (.xlsx)** ou **PDF**.

---

## Funcionalidades

- Busca em múltiplas fontes com uma única pesquisa
- Ranqueamento inteligente por relevância
- Detecção automática do idioma do artigo
- Classificação do tipo de publicação (survey, artigo de conferência, tese, artigo de journal)
- Cache local em SQLite para evitar buscas repetidas
- Exportação para Excel e PDF
- Interface gráfica em Qt6 (PySide6)

---

## Tecnologias utilizadas

| Tecnologia | Uso |
|---|---|
| Python 3.x | Linguagem principal |
| PySide6 (Qt6) | Interface gráfica |
| scikit-learn | Similaridade TF-IDF |
| pandas | Manipulação de dados |
| requests + BeautifulSoup4 | Coleta de dados das fontes |
| SQLite | Cache local de buscas |
| openpyxl / fpdf2 | Exportação para Excel e PDF |

---

## Executando a partir do código-fonte

Para desenvolvedores que preferem rodar o projeto diretamente:

```bash
git clone https://github.com/gabriel-re-pires/Busca-Artigo.git
cd Busca-Artigo/tcc_research_assistant
pip install -r requirements.txt
python main.py
```

---

## Arquitetura

O projeto segue os princípios de **Clean Architecture**, com as dependências apontando sempre para o núcleo:

```
tcc_research_assistant/
├── core/            # Entidades e exceções de domínio
├── use_cases/       # Regras de negócio (busca, filtro, ranqueamento)
├── adapters/        # Gateways de busca, exportadores e repositório de cache
└── infrastructure/  # GUI (Qt6), rede, NLP — detalhes externos
```


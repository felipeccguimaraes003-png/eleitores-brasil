# 0001. Arquitetura em camadas, verificada por ferramenta

**Status:** aceita

## Contexto
O projeto consome APIs públicas diferentes (Câmara, Senado e, em breve, TSE e IBGE) que mudam de formato sem aviso. Queremos que uma mudança numa fonte afete um único arquivo.

## Decisão
```
api  ->  services  ->  domain  <-  adapters
              (main.py é a raiz de composição: liga tudo)
```
- `domain`: modelos e portas (`ParliamentarianSource`). Só biblioteca padrão.
- `adapters`: falam HTTP com as fontes e convertem para o domínio.
- `services`: cache, combinação das fontes, resumo. Conhecem só as portas.
- `api`: FastAPI, validação de entrada, contrato público (Pydantic) e erros.

As regras são checadas no CI com **import-linter** (`pyproject.toml`): o domínio não importa `httpx`, `fastapi`, `pydantic` nem `pandas`; serviços não importam adaptadores; a API não importa adaptadores.

## Consequências
- Testamos serviços com fontes falsas e adaptadores com respostas HTTP simuladas, sem rede.
- Adicionar uma fonte (TSE, assembleias) é escrever um adaptador e registrá-lo em `main.py`.
- Custo: mais arquivos e um mapeamento domínio -> schema Pydantic.

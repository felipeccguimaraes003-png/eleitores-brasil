# 0005. Interface em mapa + painel contextual, tema claro e estado na URL

**Status:** aceita

## Contexto
O documento de orientação e o print de referência pedem uma ferramenta de navegação territorial: o mapa é o centro, e o painel mostra quem representa a região escolhida. O público é o cidadão comum, em celular, e os dados são públicos e sensíveis à confiança (um botão errado leva a um perfil falso).

## Decisão
1. **Layout:** mapa à esquerda (3/5) e painel à direita (2/5) no computador, com o mapa fixo ao rolar. No celular, as colunas empilham com o mapa primeiro.
2. **Tema:** claro e institucional (Modelo 2 do print). O Modelo 3 foi descartado por legibilidade. O escuro (Modelo 1) fica como tema opcional futuro.
3. **Navegação:** esfera (Federal, Estadual, Municipal), cargo e UF ficam na URL (`?uf=GO&esfera=federal&cargo=senador`). Cada visão é um link compartilhável, e a tela só lê a URL na primeira execução.
4. **Cargos sem dados:** aparecem desabilitados com o selo "Em preparação", em vez de sumir ou de levar a uma tela vazia.
5. **Mapa local:** cada estado é desenhado como polígono em Plotly. O `Choropleth` foi descartado: mesmo com o mapa oculto, o Plotly baixava a malha-base de `cdn.plot.ly`, o que enviava o IP do cidadão a um terceiro e impedia o mapa offline. A exportação de imagem (Kaleido) falhou por esse mesmo motivo.
6. **Contatos:** só aparecem com origem oficial (`official = true`). Qualquer contato sem essa marca é tratado como não confirmado e não gera botão.

## Consequências
- Positivo: tela clara, rápida no celular, sem terceiros no carregamento do mapa, e cada dado mostra sua origem e a data da consulta.
- Negativo: a malha é a simplificada de um repositório de terceiros até a troca pela malha oficial do IBGE. O clique no mapa depende do navegador; a lista "Seu estado" continua como alternativa completa.
- O layout foi validado com teste de tela (`AppTest`), não em navegador real. Isso fica como pendência de validação visual.

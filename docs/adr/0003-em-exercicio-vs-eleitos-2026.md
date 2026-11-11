# 0003. "Em exercício" e "eleitos 2026" são coisas diferentes

**Status:** aceita (implementação parcial)

## Contexto
As eleições de outubro de 2026 renovaram os 513 deputados federais e 54 das 81 vagas do Senado. A nova legislatura toma posse em 1º de fevereiro de 2027. Até lá, as APIs da Câmara e do Senado listam quem está em exercício, não os eleitos. Na virada de legislatura a Câmara já teve listagem com e-mail nulo durante o pré-cadastro dos eleitos.

## Decisão
- O modelo tem `MandateStatus` (`em_exercicio` implementado; `eleito_aguardando_posse` reservado).
- Hoje o app mostra somente "em exercício" e avisa na primeira tela que os eleitos assumem em 01/02/2027.
- A visão "eleitos 2026" virá dos dados do TSE (situação de totalização), com adaptador próprio.
- O cache serve o último valor bom (`stale-if-error`) para atravessar a virada sem tela vazia.

## Consequências
- Evita afirmar que alguém "é seu deputado" antes da posse.
- Em fevereiro de 2027 é preciso revisar o aviso e validar o comportamento da Câmara na virada.

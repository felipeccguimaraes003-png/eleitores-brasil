# 0004. Limitador de taxa próprio (em vez do slowapi)

**Status:** aceita

## Contexto
O primeiro desenho usava `slowapi`. O teste de integração "a 3ª requisição recebe 429" falhou: nenhuma requisição era limitada, sem erro nem aviso. Causa: o middleware do slowapi procura a rota em `app.routes`, e nas versões recentes do FastAPI as rotas de `include_router` não aparecem ali, então ele considera a rota "isenta".

## Decisão
Middleware próprio (`backend/api/ratelimit.py`, ~60 linhas, janela fixa por IP), sem depender de detalhes internos do framework. `X-Forwarded-For` é ignorado por padrão; com `TRUSTED_PROXY_HOPS=N` vale a N-ésima entrada contada do fim.

## Consequências
- Menos uma dependência e comportamento coberto por testes (janela, `Retry-After`, IP encaminhado).
- O contador é por processo: com várias réplicas, o limite principal deve ficar também no proxy reverso.
- Lição registrada: controle de segurança precisa de teste que prove que ele **bloqueia**, não só que está configurado.

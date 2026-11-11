# 0002. Todo contato tem procedência; sem fonte, não aparece

**Status:** aceita

## Contexto
O produto leva o cidadão a falar com políticos. Um Instagram ou WhatsApp errado ou falso (perfil de impostor) causa dano real, e dado pessoal publicado sem base também tem risco (LGPD, art. 7º, §3º: finalidade, boa-fé e interesse público).

## Decisão
- `ContactChannel.source` é obrigatório (ex.: `camara:deputados/204521#redeSocial`) e sai na API.
- E-mail e telefone vêm dos campos oficiais da Câmara e do Senado. Instagram vem só de rede social cadastrada pelo gabinete na Câmara (hoje) e, no próximo ciclo, do arquivo de redes sociais do TSE com correspondência forte (UF + nome civil + data de nascimento).
- Nenhum handle é preenchido "de cabeça" ou por busca fuzzy. WhatsApp: só se houver número em canal oficial; o app apenas monta um link `wa.me`, sem envio em massa.
- A sugestão da comunidade (Sprint 3) nunca publica direto: entra numa fila de moderação, com link de evidência, e é exibida só depois de verificada.

## Consequências
- Cobertura menor no início (muitos parlamentares não têm Instagram em fonte oficial), mas cada botão é confiável.
- A interface explica a ausência: "nenhum contato divulgado nas fontes oficiais".

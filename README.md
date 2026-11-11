# Eleitores Brasil (esboço do site novo)

Site com mapa clicável do Brasil que mostra quem foi eleito em 2026 em cada estado: presidente,
governador, senadores, deputados federais e deputados estaduais ou distritais. Cada pessoa tem um
perfil com as redes que declarou ao TSE, o que o cargo faz e onde está o plano de governo.

## Ver o site

```bash
cd web
python -m http.server 8080     # abra http://localhost:8080
```

Ou abra `dist/index.html` direto no navegador (arquivo único, com tudo embutido).

## Refazer os dados a partir da fonte oficial

1. Baixe do Portal de Dados Abertos do TSE (conjunto "Candidatos - 2026") os arquivos
   `consulta_cand_2026.zip` e `rede_social_candidato_2026.zip` e extraia os CSV `_BRASIL` numa pasta.
2. Rode:

```bash
pip install pandas
python scripts/build_data.py PASTA_DOS_CSV   # gera web/data/*.json
python scripts/build_page.py                 # gera dist/index.html
```

## O que é real e o que falta

- **Real:** os 1.654 eleitos titulares de 2026 e as redes sociais deles. Os dados são dos arquivos do
  TSE gerados em 05/11/2026. Neste esboço eles foram obtidos de uma cópia pública no GitHub
  (`leofn/tse-candidatos-2026`), porque o ambiente de desenvolvimento não alcança `cdn.tse.jus.br`.
  As contagens batem com as vagas oficiais (1, 27, 54, 513, 1.035 e 24). Refaça pelo passo acima
  para ter os dados direto da fonte.
- **Falta:** mandato atual (APIs da Câmara e do Senado, com e-mail e telefone de gabinete),
  prefeitos e vereadores (TSE 2024), governadores atuais (TSE 2022), fotos e atuação parlamentar.
- **Em reforma:** a pasta `backend/` (FastAPI) está no meio da migração para o modelo novo de cargos
  e ainda não serve este site. Os testes antigos do backend não passam neste estado.


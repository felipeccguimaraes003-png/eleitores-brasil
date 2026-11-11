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

## Estrutura

- `web/`: `index.html`, `app.css`, `app.js` e `data/` (eleitos e mapa). Sem bibliotecas.
- `scripts/build_data.py`: lê os CSV do TSE e gera os dados do site.
- `scripts/build_page.py`: junta tudo em `dist/index.html`.
- `data/geo/br_states.geojson`: malha simplificada dos estados (origem: repositório público
  `codeforamerica/click_that_hood`; troque pela malha oficial do IBGE antes de publicar).

## Publicar no GitHub Pages

1. Crie um repositório público vazio no GitHub (ex.: `eleitores-brasil`).
2. Na pasta do projeto: `git remote add origin https://github.com/SEU_USUARIO/eleitores-brasil.git` e `git push -u origin main`.
3. No GitHub: Settings > Pages > Source: **GitHub Actions**.
4. O workflow `.github/workflows/pages.yml` publica a pasta `web/` a cada push na `main`.
   O endereço fica `https://SEU_USUARIO.github.io/eleitores-brasil/`.

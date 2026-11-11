/* Eleitores Brasil: mapa clicável + painel de representantes.
   Sem bibliotecas. Todo dado externo entra na página por textContent (nunca por innerHTML). */
"use strict";

const UF_NAMES = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul",
  MG: "Minas Gerais", PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima",
  SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
};
const ROLE_ORDER = ["presidente", "governador", "senador", "deputado_federal", "deputado_estadual"];
const SPHERE = { presidente: "fed", senador: "fed", deputado_federal: "fed", governador: "est", deputado_estadual: "est" };
const POSSE = {
  presidente: { date: "2027-01-05", text: "5 de janeiro de 2027" },
  governador: { date: "2027-01-06", text: "6 de janeiro de 2027" },
  senador: { date: "2027-02-01", text: "1º de fevereiro de 2027" },
  deputado_federal: { date: "2027-02-01", text: "1º de fevereiro de 2027" },
  deputado_estadual: { date: null, text: "início de 2027 (a data varia por estado)" },
};
const MANDATO = { presidente: "2027 a 2031", governador: "2027 a 2031", senador: "2027 a 2035", deputado_federal: "2027 a 2031", deputado_estadual: "2027 a 2031" };
const LINK_HOSTS = new Set(["www.instagram.com", "wa.me", "www.facebook.com", "x.com", "www.youtube.com", "www.tiktok.com"]);
const NET = {
  instagram: { label: "Instagram", icon: '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".8"/>' },
  whatsapp: { label: "WhatsApp", icon: '<path d="M3 21l1.7-5A9 9 0 1 1 8 19.3z"/>' },
  facebook: { label: "Facebook", icon: '<path d="M14 8h3V4h-3a4 4 0 0 0-4 4v3H7v4h3v6h4v-6h3l1-4h-4V8z"/>' },
  x: { label: "X", icon: '<path d="M4 4l16 16M20 4L4 20"/>' },
  youtube: { label: "YouTube", icon: '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.5v5l4.5-2.5z"/>' },
  tiktok: { label: "TikTok", icon: '<path d="M14 3v11.5a3.5 3.5 0 1 1-3.5-3.5M14 3c.4 2.6 2.2 4.4 5 4.8"/>' },
};
const PARTY_COLORS = ["#1B7F4B", "#C9A400", "#1E4FB8", "#B4472E", "#6C4AB6", "#0E8C96", "#8A8F98"];

/* Poder de cada cargo. Base: Constituição Federal (artigos em cada cargo). */
const CARGOS = [
  { key: "presidente", sphere: "fed", name: "Presidente da República", mandato: "4 anos, uma reeleição seguida", vagas: "1", base: "Constituição, arts. 62, 66, 76 a 86 e 165 a 166",
    resumo: "Controla a execução do orçamento federal e nomeia quem comanda ministérios, estatais e bancos públicos. É o único cargo que cria regra com força de lei no mesmo dia, por medida provisória.",
    secoes: [
      ["Onde o presidente tem poder real", [
        "Edita medidas provisórias, que valem como lei a partir da publicação. O Congresso tem 60 dias, prorrogáveis por mais 60, para votar. Se não votar, a MP cai.",
        "Sanciona ou veta, no todo ou em parte, as leis aprovadas pelo Congresso, em até 15 dias úteis.",
        "Decide o ritmo dos gastos: pode bloquear e contingenciar verbas para cumprir a meta fiscal.",
        "Nomeia ministros e dirigentes de estatais e bancos públicos. Indica ministros do STF, o procurador-geral da República e a diretoria do Banco Central, que dependem de aprovação do Senado.",
        "Conduz a política externa e comanda as Forças Armadas."]],
      ["O dinheiro", [
        "Envia ao Congresso três leis: o PPA, plano de quatro anos; a LDO, que fixa metas e regras do ano seguinte, até 15 de abril; e a LOA, o orçamento em si, até 31 de agosto.",
        "Precisa pagar as emendas individuais e de bancada dos parlamentares: a Constituição tornou essas emendas obrigatórias. O ritmo da liberação vira moeda de troca nas votações."]],
      ["Freios e contrapesos", [
        "Todo veto volta ao Congresso, em sessão conjunta. Para derrubar, são precisos 257 votos de deputados e 41 de senadores, contados em separado. Derrubado o veto, a lei vale mesmo contra a vontade do presidente.",
        "Pode perder o cargo por crime de responsabilidade: a Câmara autoriza o processo com 342 votos, e o Senado condena com 54.",
        "Decreto que passe do limite de regulamentar a lei pode ser anulado pelo Congresso."]],
      ["Onde o presidente não manda", [
        "Não cria crime nem aumenta pena por medida provisória. A Constituição proíbe.",
        "Não comanda a Polícia Militar nem a Polícia Civil. Policiamento de rua é do governador.",
        "Não decide o buraco da sua rua, a linha de ônibus do bairro nem a coleta de lixo. Isso é da prefeitura.",
        "Não demite ministro do STF nem procurador-geral depois de nomeados."]],
      ["Como fiscalizar", [
        "Portal da Transparência: quanto o governo federal gastou, com quem e quando.",
        "Diário Oficial da União: toda nomeação, decreto e medida provisória sai ali.",
        "Tribunal de Contas da União: dá parecer sobre as contas do presidente todo ano. Quem julga as contas é o Congresso."]]] },
  { key: "governador", sphere: "est", name: "Governador", mandato: "4 anos, uma reeleição seguida", vagas: "27, uma por estado e uma no DF", base: "Constituição, arts. 25 a 28, 144 e 155",
    resumo: "Comanda a segurança pública, a rede estadual de ensino e os hospitais regionais. Arrecada o ICMS, imposto embutido na conta de luz e no combustível, que será substituído aos poucos pelo IBS a partir de 2029.",
    secoes: [
      ["Onde o governador tem poder real", [
        "Comanda a Polícia Militar, a Polícia Civil e o Corpo de Bombeiros. Escolhe os comandantes e o secretário de Segurança.",
        "Mantém as escolas estaduais, onde está a maior parte do ensino médio, e os hospitais regionais.",
        "Decide onde investir em rodovias estaduais, saneamento e obras regionais.",
        "Regula o ônibus entre cidades do estado.",
        "Sanciona ou veta as leis da Assembleia Legislativa."]],
      ["O dinheiro", [
        "Arrecada ICMS e IPVA. Um quarto do ICMS e metade do IPVA vão por lei para as prefeituras.",
        "Segue o mesmo ciclo da União: PPA, LDO e LOA, votados pela Assembleia.",
        "Deputados estaduais apresentam emendas ao orçamento, e em vários estados elas já são de pagamento obrigatório."]],
      ["Freios e contrapesos", [
        "A Assembleia pode derrubar vetos do governador, em geral pela maioria absoluta dos deputados.",
        "As contas do governo passam pelo Tribunal de Contas do Estado, que dá parecer. Quem julga é a Assembleia.",
        "Crimes comuns do governador são julgados pelo Superior Tribunal de Justiça."]],
      ["Onde o governador não manda", [
        "Se a rodovia é federal ou tem pedágio de concessão federal, o governador não pode intervir. Quem responde é o governo federal e a ANTT.",
        "Não comanda a Polícia Federal nem a Polícia Rodoviária Federal.",
        "Não asfalta rua de bairro nem define horário de ônibus municipal.",
        "Não muda salário mínimo nem regra de aposentadoria do INSS."]],
      ["Como fiscalizar", [
        "Portal da Transparência do estado.",
        "Diário Oficial do estado.",
        "Tribunal de Contas do Estado.",
        "Sessões da Assembleia Legislativa, que são públicas."]]] },
  { key: "senador", sphere: "fed", name: "Senador", mandato: "8 anos", vagas: "81, três por estado e três pelo DF", base: "Constituição, arts. 46, 52, 58 e 60",
    resumo: "Representa o estado, não a população: Roraima e São Paulo têm o mesmo peso, três cadeiras cada. É a casa que confirma ou barra os indicados para os cargos mais poderosos da República.",
    secoes: [
      ["Onde o senador tem poder real", [
        "Vota as leis federais e as emendas à Constituição. Uma PEC precisa de 49 votos, em dois turnos.",
        "Sabatina e aprova ministros do STF e o procurador-geral da República na CCJ, diretores do Banco Central na CAE e embaixadores na CRE. Sem aprovação, a nomeação não sai.",
        "Julga o presidente da República e ministros do STF por crime de responsabilidade.",
        "Autoriza empréstimos externos e fixa os limites de dívida da União, dos estados e dos municípios."]],
      ["Comissões: onde o jogo é decidido", [
        "Boa parte dos projetos é votada em comissão em caráter terminativo: aprovado ali, segue adiante sem passar pelo plenário, a não ser que 9 senadores recorram.",
        "A CCJ decide se um projeto respeita a Constituição. Um parecer contrário ali costuma enterrar a proposta.",
        "Relatoria é poder: o relator reescreve o texto antes de qualquer votação."]],
      ["O dinheiro", [
        "Cada senador tem uma cota de emendas individuais ao orçamento federal, de pagamento obrigatório. Metade precisa ir para a saúde.",
        "Divide com os deputados federais do estado as emendas de bancada, também obrigatórias.",
        "LDO e LOA passam pela Comissão Mista de Orçamento, formada por deputados e senadores. É ali que as emendas são negociadas."]],
      ["Freios e contrapesos", [
        "Derruba vetos do presidente junto com a Câmara: são precisos 41 votos no Senado.",
        "Abre CPI com 27 assinaturas, para investigar fato determinado e por prazo certo."]],
      ["Onde o senador não manda", [
        "Não executa obra. A emenda indica o destino do dinheiro; quem contrata e paga é o governo ou a prefeitura.",
        "Não vota lei estadual nem municipal.",
        "Não nomeia secretário estadual nem interfere no governo do estado."]],
      ["Como fiscalizar", [
        "Página do senador no site do Senado: votos, projetos, presença e relatorias.",
        "Portal da Transparência: emendas por autor e para onde foi o dinheiro.",
        "Portal e-Cidadania: opine sobre projetos em tramitação."]]] },
  { key: "deputado_federal", sphere: "fed", name: "Deputado federal", mandato: "4 anos", vagas: "513, de 8 a 70 por estado, conforme a população", base: "Constituição, arts. 45, 51, 58, 60 e 166",
    resumo: "Representa a população do estado: São Paulo tem 70 cadeiras, Roraima tem 8. Os projetos do governo começam pela Câmara, e é ela que autoriza processo contra o presidente.",
    secoes: [
      ["Onde o deputado tem poder real", [
        "Vota as leis federais e as emendas à Constituição. Uma PEC precisa de 308 votos, em dois turnos.",
        "Abre CPI com 171 assinaturas. A CPI tem poderes de investigação de juiz: quebra sigilo e obriga testemunhas a depor.",
        "Convoca ministros para explicações. Faltar sem justificativa é crime de responsabilidade.",
        "Autoriza, com 342 votos, que o presidente da República seja processado."]],
      ["Comissões: onde o jogo é decidido", [
        "Muitos projetos têm tramitação conclusiva: aprovados nas comissões, seguem para o Senado sem votação em plenário, salvo recurso de 52 deputados.",
        "A CCJ diz se a proposta respeita a Constituição. Presidir a CCJ ou relatar um projeto ali é das posições mais disputadas da Casa.",
        "O presidente da Câmara controla a pauta do plenário e decide se um pedido de impeachment anda ou fica na gaveta."]],
      ["O dinheiro", [
        "Emendas individuais: cada deputado indica para onde vai sua cota do orçamento. O pagamento é obrigatório, e metade vai para a saúde.",
        "Emendas de bancada: os parlamentares de cada estado decidem juntos o destino de outra fatia, também obrigatória.",
        "Emendas de comissão: definidas pelas comissões, não são obrigatórias e dependem de acordo com o governo.",
        "Parte das emendas vai como transferência especial, a emenda Pix, direto para o caixa de estados e prefeituras. Desde 2024, o STF exige plano de trabalho e rastreio desses repasses."]],
      ["Freios e contrapesos", [
        "Derruba vetos do presidente junto com o Senado: são precisos 257 votos na Câmara.",
        "Pode anular decreto do presidente que ultrapasse o que a lei permite."]],
      ["Onde o deputado não manda", [
        "Não constrói hospital nem asfalta estrada. Indica o dinheiro; quem executa é o governo ou a prefeitura, e quem audita é o TCU e a CGU.",
        "Não arruma vaga em hospital ou escola por pedido individual. Pode cobrar o órgão responsável, e é isso que deve fazer.",
        "Não vota lei estadual nem municipal."]],
      ["Como fiscalizar", [
        "Página do deputado no site da Câmara: votações, presença, projetos e gastos da cota parlamentar.",
        "Portal da Transparência: emendas por autor e para onde foi o dinheiro."]]] },
  { key: "deputado_estadual", sphere: "est", name: "Deputado estadual", mandato: "4 anos", vagas: "De 24 a 94 por estado", base: "Constituição, art. 27; no DF, art. 32",
    resumo: "Faz as leis do estado e é o principal fiscal do governador. No Distrito Federal, o deputado distrital acumula o papel de vereador, porque o DF não tem municípios.",
    secoes: [
      ["Onde o deputado estadual tem poder real", [
        "Vota as leis estaduais e as emendas à Constituição do estado.",
        "Abre CPI estadual e convoca secretários de estado.",
        "Julga as contas do governador, depois do parecer do Tribunal de Contas do Estado.",
        "Autoriza a abertura de processo de impeachment do governador."]],
      ["Comissões: onde o jogo é decidido", [
        "Como no Congresso, os projetos passam primeiro pelas comissões da Assembleia. A CCJ estadual filtra o que chega ao plenário."]],
      ["O dinheiro", [
        "Vota a LDO e a LOA do estado e apresenta emendas ao orçamento. Em muitos estados, as emendas individuais já são de pagamento obrigatório, como no Congresso."]],
      ["Freios e contrapesos", [
        "Derruba vetos do governador, em geral pela maioria absoluta dos deputados."]],
      ["Onde o deputado estadual não manda", [
        "Não vota lei federal: salário mínimo, Código Penal e regras do INSS estão fora do alcance dele.",
        "Não nomeia comandante de polícia nem diretor de escola.",
        "Não executa obra. Indica emenda; quem executa é o governo do estado."]],
      ["Como fiscalizar", [
        "Site da Assembleia Legislativa: votações, presença e verba de gabinete.",
        "Tribunal de Contas do Estado."]]] },
  { key: "prefeito", sphere: "mun", name: "Prefeito", mandato: "4 anos, uma reeleição seguida", vagas: "Um por município", base: "Constituição, arts. 29 a 31, 156, 198 e 212",
    resumo: "O cargo mais perto do seu dia a dia. Creche, posto de saúde, ônibus do bairro, lixo e o asfalto da sua rua passam pela prefeitura.",
    secoes: [
      ["Onde o prefeito tem poder real", [
        "Mantém creches, pré-escolas e escolas de ensino fundamental.",
        "Mantém as unidades básicas de saúde e a atenção primária do SUS.",
        "Cuida de ruas, iluminação pública, coleta de lixo e transporte coletivo municipal.",
        "Controla o uso do solo: alvarás, licenças de obra e, com a Câmara, o plano diretor.",
        "Sanciona ou veta as leis da Câmara Municipal."]],
      ["O dinheiro", [
        "Arrecada IPTU, ISS e ITBI e recebe repasses: parte do ICMS e do IPVA do estado e o Fundo de Participação dos Municípios, da União.",
        "Em boa parte das cidades pequenas, repasses e emendas de deputados e senadores pesam mais que a arrecadação própria.",
        "É obrigado a aplicar ao menos 25% da receita de impostos em educação e 15% em saúde."]],
      ["Freios e contrapesos", [
        "A Câmara Municipal derruba vetos, em geral por maioria absoluta, e julga as contas do prefeito.",
        "Pode ter o mandato cassado pela Câmara por infração político-administrativa."]],
      ["Onde o prefeito não manda", [
        "Não comanda a PM nem a Polícia Civil. A guarda municipal protege bens e serviços da cidade e pode patrulhar, mas não investiga crimes.",
        "Não cuida do ônibus intermunicipal nem da rodovia estadual ou federal que corta a cidade.",
        "Não decide o ensino médio da rede estadual."]],
      ["Como fiscalizar", [
        "Portal da Transparência do município.",
        "Diário Oficial do município.",
        "Ouvidoria da prefeitura.",
        "Tribunal de Contas do estado ou do município, onde houver."]]] },
  { key: "vereador", sphere: "mun", name: "Vereador", mandato: "4 anos", vagas: "De 9 a 55 por município, conforme a população", base: "Constituição, arts. 29 a 31",
    resumo: "Faz as leis da cidade e fiscaliza o prefeito. Decide o que pode ser construído em cada bairro.",
    secoes: [
      ["Onde o vereador tem poder real", [
        "Vota as leis municipais, o plano diretor e o zoneamento.",
        "Julga as contas do prefeito. O parecer do Tribunal de Contas só cai se dois terços dos vereadores votarem contra ele.",
        "Abre CPI municipal e convoca secretários.",
        "Pode cassar o mandato do prefeito por infração político-administrativa."]],
      ["O dinheiro", [
        "Vota a LDO e a LOA da cidade e apresenta emendas, que em muitos municípios são de pagamento obrigatório."]],
      ["Freios e contrapesos", [
        "Derruba vetos do prefeito, em geral por maioria absoluta."]],
      ["Onde o vereador não manda", [
        "Não asfalta rua, não troca lâmpada nem constrói posto de saúde. Pede, cobra e fiscaliza; quem executa é a prefeitura.",
        "Não pode criar cargo, órgão ou programa que gere despesa para a prefeitura. Essa iniciativa é do prefeito."]],
      ["Como fiscalizar", [
        "Site da Câmara Municipal: as sessões e votações são públicas.",
        "Tribunal de Contas do estado ou do município, onde houver."]]] },
];
const CARGO = Object.fromEntries(CARGOS.map((c) => [c.key, c]));

/* ---------- utilidades ---------- */
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid);
  return el;
}
function icon(paths) {
  const span = document.createElement("span");
  span.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`; // só constantes do código
  return span.firstChild;
}
const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const $ = (id) => document.getElementById(id);
function safeLink(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" && LINK_HOSTS.has(u.hostname) ? u.href : null;
  } catch { return null; }
}
function initials(name) {
  const t = name.split(/\s+/).filter(Boolean);
  return ((t[0] || "?")[0] + (t.length > 1 ? t[t.length - 1][0] : "")).toUpperCase();
}
function daysUntil(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const today = new Date();
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())) / 86400000);
}
function posseText(role) {
  const p = POSSE[role];
  if (!p.date) return `Toma posse no ${p.text}`;
  const n = daysUntil(p.date);
  if (n > 1) return `Toma posse em ${p.text}. Faltam ${n} dias.`;
  if (n === 1) return `Toma posse amanhã, ${p.text}.`;
  if (n === 0) return `Toma posse hoje, ${p.text}.`;
  return `Tomou posse em ${p.text}.`;
}
function roleLabel(p) {
  const fem = { Presidente: "Presidente", Governador: "Governadora", Senador: "Senadora", "Deputado Federal": "Deputada federal", "Deputado Estadual": "Deputada estadual", "Deputado Distrital": "Deputada distrital" };
  const masc = { "Deputado Federal": "Deputado federal", "Deputado Estadual": "Deputado estadual", "Deputado Distrital": "Deputado distrital" };
  return p.fem ? fem[p.label] || p.label : masc[p.label] || p.label;
}
function plural(role, uf, n) {
  const names = { presidente: ["Presidente", "Presidente"], governador: ["Governador", "Governador"], senador: ["Senador", "Senadores"],
    deputado_federal: ["Deputado federal", "Deputados federais"],
    deputado_estadual: uf === "DF" ? ["Deputado distrital", "Deputados distritais"] : ["Deputado estadual", "Deputados estaduais"] };
  return names[role][n === 1 ? 0 : 1];
}

/* ---------- estado da tela ---------- */
const state = { uf: "", cargo: "", q: "" };
let DATA = { people: [], generated: "" };
let MAP = null;
const byUF = new Map();
let president = [];

function peopleFor(uf) { return uf ? president.concat(byUF.get(uf) || []) : president; }
function setUF(uf, { focusPanel = false } = {}) {
  state.uf = UF_NAMES[uf] ? uf : "";
  state.cargo = "";
  state.q = "";
  const hash = state.uf ? `#${state.uf.toLowerCase()}` : "#inicio";
  if (location.hash !== hash) history.replaceState(null, "", hash);
  render();
  if (focusPanel && state.uf && window.matchMedia("(max-width: 900px)").matches) {
    $("painel").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }
}

/* ---------- mapa ---------- */
function buildMap() {
  const NS = "http://www.w3.org/2000/svg";
  const s = (tag, attrs) => { const el = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v); return el; };
  const svg = s("svg", { viewBox: `0 0 ${MAP.width} ${MAP.height}`, role: "group", "aria-label": "Mapa do Brasil. Escolha um estado." });
  const tip = $("dica");
  for (const st of MAP.states) {
    const g = s("g", { class: "uf", tabindex: "0", role: "button", "data-uf": st.uf, "aria-label": `${st.name}, ver representantes` });
    g.append(s("path", { d: st.d }));
    if (st.ax != null) {
      g.append(s("line", { class: "lead", x1: st.ax, y1: st.ay, x2: st.x, y2: st.y }));
      g.append(s("rect", { class: "chip", x: st.x - 17, y: st.y - 11, width: 34, height: 22, rx: 7 }));
    }
    const label = s("text", { x: st.x, y: st.y });
    label.textContent = st.uf;
    g.append(label);
    g.addEventListener("click", () => setUF(st.uf, { focusPanel: true }));
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setUF(st.uf, { focusPanel: true }); } });
    g.addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;
      const box = $("mapa").getBoundingClientRect();
      tip.textContent = st.name;
      tip.style.left = `${e.clientX - box.left}px`;
      tip.style.top = `${e.clientY - box.top}px`;
      tip.hidden = false;
    });
    g.addEventListener("pointerleave", () => { tip.hidden = true; });
    svg.append(g);
  }
  $("mapa").replaceChildren(svg);
}
function paintMap() {
  const svg = $("mapa").querySelector("svg");
  for (const g of svg.querySelectorAll(".uf")) {
    const on = g.dataset.uf === state.uf;
    g.classList.toggle("on", on);
    g.setAttribute("aria-pressed", on ? "true" : "false");
    if (on) svg.append(g); // traz o estado escolhido para a frente
  }
}

/* ---------- cartões ---------- */
function netButton(kind, link, person, big) {
  const href = safeLink(link[1]);
  if (!href || !NET[kind]) return null;
  const label = `${NET[kind].label} de ${person.name}`;
  if (big) {
    const cls = kind === "instagram" ? "btn ig" : kind === "whatsapp" ? "btn wa" : "btn ghost";
    return h("a", { class: cls, href, target: "_blank", rel: "noopener noreferrer", "aria-label": label }, icon(NET[kind].icon), NET[kind].label);
  }
  return h("a", { class: "round", href, target: "_blank", rel: "noopener noreferrer", "aria-label": label, title: NET[kind].label }, icon(NET[kind].icon));
}
function card(p) {
  const sph = SPHERE[p.role];
  const acts = [];
  for (const kind of ["instagram", "whatsapp"]) if (p.links[kind]) acts.push(netButton(kind, p.links[kind], p, true));
  for (const kind of ["facebook", "x", "youtube", "tiktok"]) if (p.links[kind]) acts.push(netButton(kind, p.links[kind], p, false));
  const buttons = acts.filter(Boolean);
  return h("article", { class: "card" },
    h("div", { class: `av ${sph}`, "aria-hidden": "true", text: initials(p.name) }),
    h("div", {},
      h("button", { class: "name", type: "button", text: p.name, onclick: () => openProfile(p) }),
      h("div", { class: "meta" },
        h("span", { class: `tag ${sph}`, text: roleLabel(p) }),
        h("span", { class: "tag", text: p.party }),
        h("span", { class: "tag soon", text: "Posse em 2027" })),
      buttons.length ? h("div", { class: "acts" }, buttons) : h("p", { class: "none", text: "Nenhuma rede informada ao TSE." })));
}
function partyBar(list) {
  const counts = new Map();
  for (const p of list) counts.set(p.party, (counts.get(p.party) || 0) + 1);
  const sorted = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const top = sorted.slice(0, 6);
  const rest = sorted.slice(6).reduce((n, [, c]) => n + c, 0);
  if (rest) top.push(["Outros", rest]);
  const bar = h("div", { class: "bar", role: "img", "aria-label": "Divisão por partido: " + top.map(([n, c]) => `${n} ${c}`).join(", ") });
  const legend = h("ul", { class: "parties" });
  top.forEach(([name, n], i) => {
    const seg = h("i"); seg.style.width = `${(n / list.length) * 100}%`; seg.style.background = PARTY_COLORS[i];
    bar.append(seg);
    const dot = h("i"); dot.style.background = PARTY_COLORS[i];
    legend.append(h("li", {}, dot, `${name} ${n}`));
  });
  return [bar, legend];
}

/* ---------- painel ---------- */
function renderPanel() {
  const panel = $("painel");
  const uf = state.uf;
  if (!uf) {
    panel.replaceChildren(
      h("h2", { class: "ptitle", text: "Brasil · eleitos em 2026" }),
      h("p", { class: "psub", text: "Resultado oficial. Os eleitos assumem em 2027." }),
      h("div", { class: "group" }, h("div", { class: "ghead" }, h("h3", { text: "Presidente da República" })), h("div", { class: "cards" }, president.map(card))),
      h("div", { class: "group" }, h("div", { class: "ghead" }, h("h3", { text: "Como usar" })),
        h("ol", { class: "steps" },
          h("li", {}, h("i", { text: "1" }), h("div", {}, h("b", { text: "Escolha o estado" }), h("span", { text: "No mapa, pela sigla ou pela busca." }))),
          h("li", {}, h("i", { text: "2" }), h("div", {}, h("b", { text: "Filtre o cargo" }), h("span", { text: "Governador, senadores e deputados." }))),
          h("li", {}, h("i", { text: "3" }), h("div", {}, h("b", { text: "Abra o perfil" }), h("span", { text: "Contato direto, o poder real do cargo e o que foi prometido." }))))),
      h("div", { class: "group" }, h("div", { class: "ghead" }, h("h3", { text: "Escolha pela sigla" })),
        h("div", { class: "ufs" }, Object.keys(UF_NAMES).sort().map((code) => h("button", { type: "button", text: code, title: UF_NAMES[code], "aria-label": UF_NAMES[code], onclick: () => setUF(code, { focusPanel: true }) })))));
    return;
  }
  const all = peopleFor(uf);
  const count = (role) => all.filter((p) => p.role === role).length;
  const pill = (role, cls, label) => h("button", { type: "button", class: `pill ${cls}`, "aria-pressed": state.cargo === role ? "true" : "false", onclick: () => { state.cargo = role; renderPanel(); } }, label, role ? h("i", { text: String(count(role)) }) : h("i", { text: String(all.length) }));
  const filterBox = h("input", { class: "filter", id: "filtro", type: "search", placeholder: "Filtrar por nome ou partido", "aria-label": "Filtrar por nome ou partido", value: state.q });
  const listBox = h("div", {});
  filterBox.addEventListener("input", () => { state.q = filterBox.value; drawList(); });

  function drawList() {
    const needle = fold(state.q.trim());
    const match = (p) => !needle || fold(p.name).includes(needle) || fold(p.full).includes(needle) || fold(p.party).includes(needle);
    const out = [];
    const roles = state.cargo ? [state.cargo] : ROLE_ORDER;
    let shown = 0;
    for (const role of roles) {
      const list = all.filter((p) => p.role === role && match(p));
      if (!list.length) continue;
      shown += list.length;
      const limit = state.cargo || needle ? list.length : 4;
      const head = h("div", { class: "ghead" }, h("h3", { text: `${plural(role, uf, list.length)} · ${list.length}` }));
      if (list.length > limit) head.append(h("button", { class: "more", type: "button", text: `Ver os ${list.length}`, onclick: () => { state.cargo = role; renderPanel(); } }));
      const group = h("div", { class: "group" }, head);
      if (state.cargo && list.length > 8) group.append(...partyBar(list));
      group.append(h("div", { class: "cards" }, list.slice(0, limit).map(card)));
      out.push(group);
    }
    if (!shown) out.push(h("p", { class: "empty", text: "Nenhum resultado. Tente outro nome ou partido, ou escolha Todos." }));
    listBox.replaceChildren(...out);
  }

  panel.replaceChildren(
    h("h2", { class: "ptitle", text: `Eleitos 2026 · ${UF_NAMES[uf]}` }),
    h("p", { class: "psub", text: "Quem assume em 2027, por cargo." }),
    h("div", { class: "pills", role: "group", "aria-label": "Filtrar por cargo" },
      pill("", "all", "Todos"), pill("presidente", "fed", "Presidente"), pill("governador", "est", "Governador"),
      pill("senador", "fed", "Senadores"), pill("deputado_federal", "fed", "Dep. federais"),
      pill("deputado_estadual", "est", uf === "DF" ? "Dep. distritais" : "Dep. estaduais"),
      h("button", { type: "button", class: "pill mun", disabled: true, text: "Prefeito e vereadores · em breve" })),
    filterBox, listBox);
  drawList();
}

function renderStage() {
  const uf = state.uf;
  $("titulo-mapa").textContent = uf ? UF_NAMES[uf] : "Quem representa você?";
  $("sub-mapa").textContent = uf ? "Clique em outro estado para trocar." : "Clique no seu estado para ver quem foi eleito em 2026.";
  const trail = $("trilha");
  trail.replaceChildren(...(uf
    ? [h("a", { href: "#inicio", text: "Início", onclick: (e) => { e.preventDefault(); setUF(""); } }), h("span", { "aria-hidden": "true", text: "›" }), h("b", { "aria-current": "page", text: UF_NAMES[uf] })]
    : [h("b", { "aria-current": "page", text: "Início" })]));
  const list = uf ? byUF.get(uf) || [] : DATA.people;
  const n = (role) => list.filter((p) => p.role === role).length;
  const withIg = list.filter((p) => p.links.instagram).length;
  const tile = (cls, value, label) => h("div", { class: `tile ${cls}` }, h("b", { text: String(value) }), h("span", { text: label }));
  $("numeros").replaceChildren(
    tile("", n("deputado_federal"), "deputados federais"), tile("", n("senador"), "senadores eleitos"),
    tile("est", n("deputado_estadual"), uf === "DF" ? "deputados distritais" : "deputados estaduais"),
    tile("blue", `${Math.round((withIg / Math.max(list.length, 1)) * 100)}%`, "com Instagram informado"));
}
function render() { paintMap(); renderStage(); renderPanel(); }

/* ---------- perfil ---------- */
function openProfile(p) {
  const dlg = $("perfil");
  const c = CARGO[p.role];
  const sph = SPHERE[p.role];
  const where = p.uf ? UF_NAMES[p.uf] : "Brasil";
  const body = h("div", { class: "dbody" });
  const tabs = [
    ["Contato", () => {
      const rows = Object.entries(p.links).map(([kind, link]) => {
        const href = safeLink(link[1]);
        return href && NET[kind] ? h("a", { class: "linkrow", href, target: "_blank", rel: "noopener noreferrer" }, icon(NET[kind].icon), h("b", { text: NET[kind].label }), h("span", { text: link[0] })) : null;
      }).filter(Boolean);
      for (const row of rows) { row.firstChild.setAttribute("width", "18"); row.firstChild.setAttribute("height", "18"); row.firstChild.style.cssText = "fill:none;stroke:currentColor;stroke-width:2;flex:none"; }
      return [h("div", { class: "sec" }, h("h3", { text: "Fale direto" }),
        rows.length ? h("div", { class: "links" }, rows) : h("p", { text: "Não declarou nenhuma rede social ao TSE." }),
        h("p", { class: "none", text: "Endereços declarados pela própria candidatura ao TSE. E-mail e telefone de gabinete só existem depois da posse." })),
      h("div", { class: "sec" }, h("h3", { text: "Ficha" }), h("div", { class: "facts" },
        fact("Nome completo", p.full), fact("Partido", p.party), fact("Número na urna", p.num),
        fact("Resultado", p.result === "ELEITO" ? `Eleito no ${p.round}º turno` : p.result === "ELEITO POR QP" ? "Eleito por quociente partidário" : "Eleito por média"),
        fact("Mandato", MANDATO[p.role]), p.vice ? fact("Vice", p.vice) : null))];
    }],
    ["Poder do cargo", () => [
      h("div", { class: "sec" }, h("h3", { text: c.name }), h("p", { text: c.resumo }), h("p", { class: "none", text: `Mandato: ${c.mandato}. Vagas: ${c.vagas}. ${c.base}.` })),
      ...c.secoes.map(([titulo, itens]) => h("div", { class: "sec" }, h("h3", { text: titulo }), h("ul", {}, itens.map((t) => h("li", { text: t })))))]],
    ["O que prometeu", () => (p.role === "presidente" || p.role === "governador")
      ? [h("div", { class: "sec" }, h("h3", { text: "O compromisso por escrito" }),
          h("p", { text: `O plano de governo é o único compromisso escrito que a lei exige. Presidente, governador e prefeito entregam o documento ao TSE no registro da candidatura (Lei 9.504/1997, art. 11). Ninguém é punido por descumprir, mas é com ele que você compara o que ${p.name} prometeu com o que entregar.` }),
          h("p", {}, "Como achar: abra o ", h("a", { href: "https://divulgacandcontas.tse.jus.br/divulga/#/home", target: "_blank", rel: "noopener noreferrer", text: "DivulgaCandContas" }), `, escolha ${where}, depois Candidaturas, o cargo e o número ${p.num}. As propostas ficam na aba Propostas.`))]
      : [h("div", { class: "sec" }, h("h3", { text: "O plano é o voto" }),
          h("p", { text: "A lei não cobra metas de quem legisla. O verdadeiro plano de governo de um parlamentar é o seu histórico de votações." }),
          h("p", { text: "Compare o discurso de campanha com três coisas: como vota nos projetos que pesam no seu bolso, que projetos apresenta e para onde manda as emendas. Pergunte direto pelas redes da aba Contato." }))]],
    ["O que vem fazendo", () => [h("div", { class: "sec" }, h("h3", { text: "Ainda não assumiu" }),
      h("p", { text: posseText(p.role) }),
      h("p", { text: "A partir da posse, esta aba mostra como vota, que projetos apresenta, em que comissões atua e quanto gasta." }))]],
  ];
  const tabBar = h("div", { class: "tabs", role: "tablist" });
  const tabBody = h("div", { class: "dbody" });
  tabBody.style.padding = "0";
  tabs.forEach(([label, build], i) => {
    const b = h("button", { type: "button", role: "tab", "aria-selected": i === 0 ? "true" : "false", text: label, onclick: () => {
      for (const t of tabBar.children) t.setAttribute("aria-selected", t === b ? "true" : "false");
      tabBody.replaceChildren(...build());
    } });
    tabBar.append(b);
  });
  tabBody.replaceChildren(...tabs[0][1]());
  body.append(h("p", { class: "count", text: posseText(p.role) }), tabBar, tabBody);
  dlg.replaceChildren(
    h("div", { class: `dhead ${sph === "est" ? "est" : ""}` },
      h("div", { class: `av big ${sph}`, "aria-hidden": "true", text: initials(p.name) }),
      h("div", {}, h("h2", { id: "perfil-nome", text: p.name }), h("p", { text: `${roleLabel(p)} eleito${p.fem ? "a" : ""} · ${p.party} · ${where}` })),
      h("button", { class: "x", type: "button", "aria-label": "Fechar", text: "×", onclick: () => dlg.close() })),
    body);
  dlg.showModal();
  dlg.scrollTop = 0;
}
function fact(label, value) { return h("div", { class: "fact" }, h("small", { text: label }), h("b", { text: value })); }

/* ---------- janelas de apoio ---------- */
function openCargos() {
  const dlg = $("cargos");
  const names = { fed: "Federal", est: "Estadual", mun: "Municipal" };
  dlg.replaceChildren(
    h("div", { class: "dhead" }, h("div", {}, h("h2", { id: "cargos-titulo", text: "Quem manda em quê" }), h("p", { text: "Do Planalto à Câmara Municipal: onde cada cargo tem poder, de onde vem o dinheiro e como cobrar." })),
      h("button", { class: "x", type: "button", "aria-label": "Fechar", text: "×", onclick: () => dlg.close() })),
    h("div", { class: "dbody" }, h("div", { class: "roles" }, CARGOS.map((c) => h("section", { class: `role ${c.sphere}` },
      h("small", { text: `${names[c.sphere]} · mandato de ${c.mandato}` }), h("h3", { text: c.name }), h("p", { text: c.resumo }),
      ...c.secoes.flatMap(([titulo, itens]) => [h("h4", { text: titulo }), h("ul", {}, itens.map((t) => h("li", { text: t })))]),
      h("small", { text: c.base }))))));
  dlg.showModal();
}

/* ---------- busca do topo ---------- */
function setupSearch() {
  const input = $("busca");
  const box = $("sugestoes");
  const close = () => { box.hidden = true; box.replaceChildren(); };
  input.addEventListener("input", () => {
    const q = fold(input.value.trim());
    if (q.length < 2) return close();
    const items = [];
    for (const [code, name] of Object.entries(UF_NAMES)) {
      if (fold(name).includes(q) || code.toLowerCase() === q) items.push({ label: name, detail: "Estado", go: () => setUF(code, { focusPanel: true }) });
    }
    for (const p of DATA.people) {
      if (items.length >= 9) break;
      if (fold(p.name).includes(q) || fold(p.full).includes(q)) items.push({ label: p.name, detail: `${roleLabel(p)} · ${p.party} · ${p.uf || "Brasil"}`, go: () => { if (p.uf) setUF(p.uf); openProfile(p); } });
    }
    if (!items.length) { box.replaceChildren(h("li", {}, h("button", { type: "button", disabled: true, text: "Nada encontrado" }))); box.hidden = false; return; }
    box.replaceChildren(...items.map((it) => h("li", {}, h("button", { type: "button", onclick: () => { close(); input.value = ""; it.go(); } }, h("b", { text: it.label }), h("small", { text: it.detail })))));
    box.hidden = false;
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
    if (e.key === "Enter") { const first = box.querySelector("button:not([disabled])"); if (first) first.click(); }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) close(); });
}

/* ---------- início ---------- */
async function loadJSON(id, url) {
  const embedded = document.getElementById(id);
  if (embedded) return JSON.parse(embedded.textContent);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Falha ao carregar ${url}`);
  return res.json();
}
function setupTheme() {
  let saved = null;
  try { saved = localStorage.getItem("eb-tema"); } catch { /* sem armazenamento */ }
  if (saved) document.documentElement.dataset.theme = saved;
  $("tema").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("eb-tema", root.dataset.theme); } catch { /* sem armazenamento */ }
  });
}
async function start() {
  setupTheme();
  try {
    [DATA, MAP] = await Promise.all([loadJSON("dados-eleitos", "data/eleitos-2026.json"), loadJSON("dados-mapa", "data/br-map.json")]);
  } catch (err) {
    $("painel").replaceChildren(h("p", { class: "empty", text: "Os dados não carregaram. Recarregue a página." }));
    return;
  }
  for (const p of DATA.people) {
    if (!p.uf) president.push(p);
    else { if (!byUF.has(p.uf)) byUF.set(p.uf, []); byUF.get(p.uf).push(p); }
  }
  for (const list of byUF.values()) list.sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || a.name.localeCompare(b.name, "pt-BR"));
  buildMap();
  setupSearch();
  $("abrir-cargos").addEventListener("click", openCargos);
  $("brand").addEventListener("click", (e) => { e.preventDefault(); setUF(""); });
  for (const dlg of document.querySelectorAll("dialog")) dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  const fromHash = () => setUF(location.hash.slice(1).toUpperCase());
  window.addEventListener("hashchange", fromHash);
  fromHash();
}
start();

'use strict';
const $ = id => document.getElementById(id);
const API_VERSION = 1;
const POLL_INTERVAL = 1000;
let catalog=[], images=[], current=null, film='kodak_portra_400', paper='kodak_portra_endura', brand='all', busy=false, comparing=true;
const defaults={exposure:0,yellow:0,magenta:0,grain_size:.2,grain_blur:.65,halation:1,scatter:1};
const controls=[['exposure-control','exposure','Compensação · EV',-3,3,.1],['color-controls','yellow','Filtro amarelo',-50,50,.5],['color-controls','magenta','Filtro magenta',-50,50,.5],['grain-controls','grain_size','Área das partículas · µm²',.01,2,.01],['grain-controls','grain_blur','Suavização',0,2,.05],['halation-controls','halation','Intensidade de halation',0,3,.05],['halation-controls','scatter','Dispersão da luz',0,3,.05]];
for(const [parent,id,label,min,max,step] of controls){const div=document.createElement('div');div.className='control';div.innerHTML=`<label for="${id}">${label}<output id="${id}-value">${defaults[id]}</output></label><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${defaults[id]}"><div class="range-labels"><span>${min}</span><span>${max}</span></div>`;$(parent).append(div);$(id).oninput=()=>{$(`${id}-value`).value=$(id).value;dirty();};}
function status(message){$('status').textContent=message;}
function dirty(){if(!busy&&current?.result)status('Ajustes alterados · gere uma nova prévia');}
function enabled(){$('drop').setAttribute('aria-busy',String(busy));for(const id of ['preview','render'])$(id).disabled=!current||busy;$('open').disabled=busy;$('empty-open').disabled=busy;$('export').disabled=!current?.result||busy;}
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const error = Error(data.error || 'Falha na solicitação');
    error.status = response.status;
    throw error;
  }
  return data;
}
function logClientError(error, context) {
  console.error('[Spektrafilm] ' + context, error);
  // Diagnostics must never block an operation or trigger more diagnostics.
  void fetch('/api/client-error', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({context, message:String(error.message || error).slice(0,2000), stack:String(error.stack || '').slice(0,8000)}),
  }).catch(() => {});
}
async function ensureBackend() {
  let health;
  try { health = await api('/api/health'); }
  catch (error) {
    throw Error('Servidor indisponível ou desatualizado. Reinicie spektrafilm-web e atualize a página.');
  }
  if (health.api_version !== API_VERSION) {
    throw Error('A interface e o servidor estão em versões diferentes. Reinicie spektrafilm-web e atualize a página.');
  }
  return health;
}
function stockButton(p,isPaper=false){const button=document.createElement('button');button.className='stock'+((isPaper?paper:film)===p.id?' selected':'');button.setAttribute('aria-pressed',String((isPaper?paper:film)===p.id));const swatch=document.createElement('span');const maker=p.id.startsWith('kodak')?'kodak':p.id.startsWith('fujifilm')?'fuji':'other';swatch.className='swatch '+maker;swatch.textContent=maker==='kodak'?'KODAK':maker==='fuji'?'FUJI':'FILM';const text=document.createElement('span');text.textContent=p.name;const small=document.createElement('small');small.textContent=isPaper?'Papel fotográfico':p.type==='positive'?'Diapositivo / positivo':p.channel_model==='bw'?'Preto e branco':'Negativo colorido';text.append(small);button.append(swatch,text);button.onclick=()=>{if(isPaper)paper=p.id;else film=p.id;drawLibrary();dirty();};return button;}
function drawLibrary(){const query=$('search').value.toLowerCase();const films=catalog.filter(p=>p.support==='film');$('count').textContent=films.length;const filtered=films.filter(p=>(brand==='all'||(brand==='other'?!['kodak','fujifilm'].some(b=>p.id.startsWith(b)):p.id.startsWith(brand)))&&p.name.toLowerCase().includes(query));$('stocks').replaceChildren();for(const [name,match] of [['Negativo colorido',p=>p.type!=='positive'&&p.channel_model!=='bw'&&p.use!=='cine'],['Preto e branco',p=>p.channel_model==='bw'],['Slide / positivo',p=>p.type==='positive'&&p.channel_model!=='bw'],['Cinema',p=>p.use==='cine'&&p.type!=='positive'&&p.channel_model!=='bw']]){const rows=filtered.filter(match);if(!rows.length)continue;const title=document.createElement('h3');title.className='group-title';title.textContent=name;$('stocks').append(title,...rows.map(p=>stockButton(p)));}if(!filtered.length)$('stocks').textContent='Nenhum filme encontrado.';$('papers').replaceChildren(...catalog.filter(p=>p.support==='paper').map(p=>stockButton(p,true)));$('paper-select').value=paper;$('selected-film').textContent=catalog.find(p=>p.id===film)?.name||film;}
$('search').oninput=drawLibrary;document.querySelectorAll('[data-brand]').forEach(b=>b.onclick=()=>{brand=b.dataset.brand;document.querySelectorAll('[data-brand]').forEach(x=>x.classList.toggle('active',x===b));drawLibrary();});$('paper-select').onchange=()=>{paper=$('paper-select').value;drawLibrary();dirty();};
function resize(){if(!current)return;const canvas=$('canvas'),zoom=$('zoom').value;const scale=zoom==='fit'?Math.min(canvas.clientWidth/current.width,canvas.clientHeight/current.height):Number(zoom)/100;$('frame').style.width=current.width*scale+'px';$('frame').style.height=current.height*scale+'px';}
function comparison(){const has=Boolean(current?.result);$('processed').hidden=!has;$('result-label').hidden=!has;$('split').hidden=!has||!comparing;$('divider').hidden=!has||!comparing;$('processed').style.clipPath=`inset(0 0 0 ${comparing?$('split').value:0}%)`;$('divider').style.left=$('split').value+'%';$('compare').setAttribute('aria-pressed',String(comparing));}
$('split').oninput=comparison;$('compare').onclick=()=>{comparing=!comparing;comparison();};$('zoom').onchange=resize;new ResizeObserver(resize).observe($('drop'));
function activate(image){if(busy)return;current=image;$('empty').hidden=true;$('canvas').hidden=false;$('original').src=image.url;if(image.result)$('processed').src=image.result.url;else $('processed').removeAttribute('src');$('filename').textContent=image.name;$('metadata').textContent=`${image.width} × ${image.height} · ${image.space}`;$('space').value=image.space;$('encoded').checked=image.encoded;document.querySelectorAll('.thumb').forEach(b=>b.classList.toggle('selected',b.dataset.id===image.id));resize();comparison();enabled();status(image.result?'Simulação concluída':'Imagem pronta · escolha um filme');}
function formatDuration(value) {
  if (!Number.isFinite(value)) return '—';
  const seconds = Math.max(0, Math.ceil(value));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ${seconds % 60} s`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}
function updateTiming(timing) {
  $('progress-timing').hidden = !timing;
  if (!timing) return;
  $('elapsed-time').textContent = `Decorrido: ${formatDuration(timing.elapsed_seconds ?? 0)}`;
  let remaining = 'Calculando estimativa…';
  if (timing.eta_state === 'displaying') remaining = 'Carregando visualização…';
  else if (timing.status === 'error' || timing.eta_state === 'error') remaining = 'Estimativa indisponível';
  else if (timing.status === 'done' || timing.eta_state === 'done') remaining = 'Concluído';
  else if (timing.eta_state === 'recalculating') remaining = 'Recalculando estimativa…';
  else if (Number.isFinite(timing.remaining_seconds) && timing.remaining_seconds > 0) {
    remaining = `Restante: aprox. ${formatDuration(timing.remaining_seconds)}`;
  }
  $('remaining-time').textContent = remaining;
}
function progress(value, stage, title, timing = null) {
  updateTiming(timing);
  const panel = $('task-progress');
  panel.hidden = false;
  panel.dataset.state = 'running';
  $('progress-bar').value = Math.max(0, Math.min(100, value));
  $('progress-percent').textContent = Math.floor($('progress-bar').value) + '%';
  $('progress-title').textContent = title;
  $('progress-detail').textContent = stage;
  status(stage);
}
function finishProgress(message, error = false) {
  $('task-progress').dataset.state = error ? 'error' : 'done';
  if (!error) {
    $('progress-bar').value = 100;
    $('progress-percent').textContent = '100%';
  }
  $('progress-detail').textContent = message;
  if (!$('progress-timing').hidden) {
    $('remaining-time').textContent = error ? 'Estimativa indisponível' : 'Concluído';
  }
  status(message);
}
async function watchUpload(job, update, signal) {
  // Allow a short race while the POST creates the job, then stop on failure.
  let failures = 0;
  let lastProgress = 0;
  while (!signal.aborted) {
    try {
      const response = await fetch('/api/jobs/' + job, {signal});
      if (response.status === 404) {
        failures++;
      } else {
        const state = await response.json();
        if (!response.ok) throw Error(state.error || 'Falha ao consultar importação');
        failures = 0;
        lastProgress = state.progress ?? lastProgress;
        if (!signal.aborted) update(state);
        if (state.status !== 'running') return;
      }
    } catch (error) {
      if (signal.aborted) return;
      failures++;
    }
    if (failures >= 3 && !signal.aborted) {
      const error = Error('O servidor não está fornecendo o progresso da importação. Aguardando a resposta do arquivo; se persistir, reinicie spektrafilm-web.');
      logClientError(error, 'upload progress job=' + job);
      update({progress:lastProgress, stage:error.message});
      return;
    }
    await new Promise(resolve => {
      const done = () => { clearTimeout(timer); signal.removeEventListener('abort', done); resolve(); };
      const timer = setTimeout(done, POLL_INTERVAL);
      signal.addEventListener('abort', done, {once:true});
      if (signal.aborted) done();
    });
  }
}
async function readyImage(url) {
  const image = new Image();
  image.src = url;
  await image.decode();
}
async function upload(files) {
  const queue = Array.from(files);
  if (busy || !queue.length) return;
  busy = true;
  enabled();
  const title = `Importando ${queue.length} ${queue.length === 1 ? 'foto' : 'fotos'}`;
  try {
    progress(0, 'Verificando conexão com o servidor', title);
    const backend = await ensureBackend();
    for (const [index, file] of queue.entries()) {
      const label = `${index + 1}/${queue.length} · ${file.name}`;
      const job = crypto.randomUUID().replaceAll('-', '');
      const controller = new AbortController();
      const update = state => progress((index + Math.min(state.progress ?? 0, 99) / 100) / queue.length * 100, `${label} · ${state.stage}`, title);
      progress(index / queue.length * 100, `${label} · Iniciando importação`, title);
      const watching = watchUpload(job, update, controller.signal);
      let image;
      try {
        image = await api('/api/upload', {method:'POST', headers:{'X-Filename':encodeURIComponent(file.name), 'X-Upload-ID':job}, body:file});
      } finally {
        controller.abort();
        await watching;
      }
      progress((index + .99) / queue.length * 100, `${label} · Exibindo miniatura`, title);
      await readyImage(image.url);
      image.name = file.name;
      image.serverSession = backend.session;
      images.push(image);
      if (images.length === 1) $('filmstrip').replaceChildren();
      const button = document.createElement('button');
      button.className = 'thumb';
      button.dataset.id = image.id;
      button.title = file.name;
      const img = document.createElement('img');
      img.src = image.url;
      img.alt = file.name;
      button.append(img);
      button.onclick = () => activate(image);
      $('filmstrip').append(button);
      busy = false;
      activate(image);
      busy = true;
      enabled();
      progress((index + 1) / queue.length * 100, `${label} · Imagem pronta`, title);
    }
    finishProgress(`${queue.length} ${queue.length === 1 ? 'foto importada' : 'fotos importadas'}`);
  } catch (error) {
    logClientError(error, 'upload');
    finishProgress(`Importação interrompida · ${error.message}`, true);
  } finally {
    busy = false;
    enabled();
    $('files').value = '';
  }
}
$('open').onclick=$('empty-open').onclick=()=>$('files').click();$('files').onchange=()=>upload($('files').files);$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('drag');};$('drop').ondragleave=()=>$('drop').classList.remove('drag');$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('drag');upload(e.dataTransfer.files);};
async function render(mode) {
  if (!current || busy) return;
  busy = true;
  enabled();
  const image = current;
  const title = mode === 'full' ? 'Renderização' : 'Prévia espectral';
  progress(0, 'Iniciando simulação…', title, {elapsed_seconds:0});
  try {
    const backend = await ensureBackend();
    if (image.serverSession && image.serverSession !== backend.session) {
      throw Error('O servidor foi reiniciado. Reabra as fotos antes de renderizar.');
    }
    const data = {image:image.id, film, paper, mode, space:$('space').value, encoded:$('encoded').checked, grain:$('grain').checked};
    for (const id of Object.keys(defaults)) data[id] = Number($(id).value);
    const {job} = await api('/api/render', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    let result;
    do {
      try {
        result = await api('/api/jobs/' + job);
      } catch (error) {
        if (error.status === 404) throw Error('O processamento não existe neste servidor. Reabra as fotos e tente novamente.');
        throw error;
      }
      progress(Math.min(result.progress ?? 0, 99), result.stage || 'Processando…', title, result);
      if (result.status === 'running') await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
    } while (result.status === 'running');
    if (result.status === 'error') throw Error(result.error);
    progress(99, 'Carregando o resultado na visualização', title, {...result, eta_state:'displaying'});
    await readyImage(result.url);
    image.result = result;
    $('processed').src = result.url;
    comparison();
    finishProgress(result.preview ? 'Prévia pronta · renderize para incluir grão e resolução completa' : 'Renderização · pronta para exportar');
  } catch (error) {
    logClientError(error, 'render');
    finishProgress(error.message, true);
  } finally {
    busy = false;
    enabled();
  }
}
$('preview').onclick=()=>render('preview');$('render').onclick=()=>render('full');$('export').onclick=()=>{const result=current.result;$('export-note').textContent=result.preview?'Esta é uma prévia reduzida, sem grão. Use Renderizar para exportar em resolução completa.':'Imagem em resolução completa · sRGB. TIFF em 16 bits.';$('downloads').replaceChildren();for(const [ext,url] of Object.entries(result.exports)){const a=document.createElement('a');a.href=url;a.download=current.name.replace(/\.[^.]+$/,'')+'-spektrafilm.'+ext;a.textContent=ext.toUpperCase();$('downloads').append(a);}$('export-dialog').showModal();};
$('basic').onclick=()=>{$('advanced-panel').hidden=true;$('basic').classList.add('active');$('advanced').classList.remove('active');};$('advanced').onclick=()=>{$('advanced-panel').hidden=false;$('advanced').classList.add('active');$('basic').classList.remove('active');};$('reset').onclick=()=>{for(const [id,value] of Object.entries(defaults)){$(id).value=value;$(`${id}-value`).value=value;}$('grain').checked=true;dirty();};for(const id of ['space','encoded','grain'])$(id).onchange=dirty;
api('/api/profiles').then(data=>{catalog=data;for(const p of catalog.filter(p=>p.support==='paper')){const option=document.createElement('option');option.value=p.id;option.textContent=p.name;$('paper-select').append(option);}drawLibrary();}).catch(e=>status(e.message));

window.addEventListener('error', event => {
  logClientError(event.error || Error(event.message), 'uncaught error');
});
window.addEventListener('unhandledrejection', event => {
  logClientError(event.reason || Error('Unhandled promise rejection'), 'unhandled rejection');
});

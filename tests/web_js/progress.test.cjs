const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

// A minimal DOM double exercises async UI state; this is not browser QA.
function app(respond, health = {api_version:1,session:'test-session'}) {
  const history = [];
  const elements = new Map();
  function element(id = '') {
    let text = '';
    return {
      id, value: id === 'zoom' ? 'fit' : 0, checked:true, hidden:true,
      clientWidth:600, clientHeight:400, dataset:{}, style:{}, children:[],
      classList:{add(){}, remove(){}, toggle(){}},
      append(...items){this.children.push(...items);},
      replaceChildren(...items){this.children=items;},
      setAttribute(){}, removeAttribute(){},
      get textContent(){return text;},
      set textContent(value){text=value;if(id.startsWith('progress-'))history.push([id,value]);},
    };
  }
  const document = {
    getElementById(id){if(!elements.has(id))elements.set(id,element(id));return elements.get(id);},
    querySelectorAll(){return [];}, createElement(){return element();},
  };
  const context = vm.createContext({document,crypto:webcrypto,AbortController,
    window:{addEventListener(){}},
    setTimeout:(fn,ms)=>setTimeout(fn, Math.min(ms,5)), clearTimeout,
    ResizeObserver:class {observe(){}}, Image:class {async decode(){}},
    fetch:async (url, options) => {
      if(url === '/api/profiles')return {ok:true,json:async()=>[]};
      if(url === '/api/health')return health === null ? {ok:false,status:404,json:async()=>({error:'Not found'})} : {ok:true,json:async()=>health};
      if(url === '/api/client-error')return {ok:true,json:async()=>({ok:true})};
      return respond(url,options);
    },
  });
  vm.runInContext(readFileSync('src/spektrafilm_web/static/app.js','utf8'),context);
  return {context, history, get:id=>document.getElementById(id), run:code=>vm.runInContext(code,context)};
}
const response = (data,status=200) => ({ok:status<400,status,json:async()=>data});

 test('batch import reports each file, aggregate progress and completion', async()=>{
  let uploads=0;
  const ui=app(async(url,options)=>{
    if(url.startsWith('/api/jobs/'))return response({status:'running',progress:70,stage:'Convertendo cores'});
    uploads++;
    await new Promise(resolve=>setTimeout(resolve,10));
    return response({id:String(uploads),url:'/image.png',width:32,height:32,space:'sRGB',encoded:true});
  });
  await ui.run("upload([{name:'a.jpg'},{name:'b.jpg'}])");
  assert.equal(uploads,2);
  assert.equal(ui.get('progress-bar').value,100);
  assert.equal(ui.get('task-progress').dataset.state,'done');
  assert.equal(ui.get('progress-detail').textContent,'2 fotos importadas');
  assert.ok(ui.history.some(([id,text])=>id==='progress-detail'&&text.includes('1/2 · a.jpg · Convertendo cores')));
  assert.ok(ui.history.some(([id,text])=>id==='progress-detail'&&text.includes('2/2 · b.jpg')));
  assert.ok(ui.history.some(([id,text])=>id==='progress-percent'&&text==='35%'));
  assert.equal(ui.get('open').disabled,false);
});

test('failed import preserves partial progress and permits retry',async()=>{
  let uploads=0;
  const ui=app(async(url)=>{
    if(url.startsWith('/api/jobs/'))return response({status:'running',progress:45,stage:'Lendo imagem'});
    uploads++;
    if(uploads===2)return response({error:'Arquivo inválido'},400);
    return response({id:'one',url:'/image.png',width:32,height:32,space:'sRGB',encoded:true});
  });
  await ui.run("upload([{name:'a.jpg'},{name:'bad.jpg'}])");
  assert.equal(ui.get('task-progress').dataset.state,'error');
  assert.ok(ui.get('progress-bar').value < 100);
  assert.match(ui.get('progress-detail').textContent,/Arquivo inválido/);
  assert.equal(ui.get('open').disabled,false);
  assert.equal(ui.run('images.length'),1);
  assert.equal(ui.run('busy'),false);
});

test('render follows reported stages and reaches 100 only after completion',async()=>{
  const states=[{status:'running',progress:8,stage:'Preparando modelos'},
    {status:'running',progress:35,stage:'Revelando filme'},
    {status:'running',progress:96,stage:'Gravando TIFF'},
    {status:'done',progress:100,stage:'Concluído',url:'/result.png',exports:{png:'/result.png'},preview:false}];
  const ui=app(async(url)=>response(url==='/api/render'?{job:'render'}:states.shift()));
  ui.run("current={id:'one',width:32,height:32};");
  await ui.run("render('full')");
  assert.ok(ui.history.some(([id,text])=>id==='progress-detail'&&text==='Revelando filme'));
  assert.ok(ui.history.some(([id,text])=>id==='progress-detail'&&text==='Gravando TIFF'));
  assert.equal(ui.get('progress-bar').value,100);
  assert.equal(ui.get('task-progress').dataset.state,'done');
  assert.equal(ui.get('export').disabled,false);
});

test('render failure stays below 100 and unlocks controls',async()=>{
  const ui=app(async(url)=>response(url==='/api/render'?{job:'render'}:{status:'error',progress:35,stage:'Falha',error:'Sem memória'}));
  ui.run("current={id:'one'};");
  await ui.run("render('full')");
  assert.equal(ui.get('task-progress').dataset.state,'error');
  assert.equal(ui.get('progress-bar').value,35);
  assert.equal(ui.get('progress-detail').textContent,'Sem memória');
  assert.equal(ui.get('render').disabled,false);
});

test('old backend blocks import with restart message before sending the photo',async()=>{
  let requests=0;
  const ui=app(async()=>{requests++;return response({});},null);
  await ui.run("upload([{name:'a.jpg'}])");
  assert.equal(requests,0);
  assert.match(ui.get('progress-detail').textContent,/Reinicie spektrafilm-web/);
  assert.equal(ui.get('task-progress').dataset.state,'error');
  assert.equal(ui.run('busy'),false);
});

test('incompatible backend blocks render without creating a job',async()=>{
  let requests=0;
  const ui=app(async()=>{requests++;return response({});},{api_version:999,session:'other'});
  ui.run("current={id:'one'};");
  await ui.run("render('full')");
  assert.equal(requests,0);
  assert.match(ui.get('progress-detail').textContent,/versões diferentes/);
  assert.equal(ui.get('render').disabled,false);
});

test('upload polling stops after three missing-job responses',async()=>{
  let polls=0;
  const ui=app(async()=>{polls++;return response({error:'Job not found'},404);});
  await ui.run("watchUpload('missing',state=>progress(state.progress,state.stage,'Upload'),new AbortController().signal)");
  assert.equal(polls,3);
  assert.match(ui.get('progress-detail').textContent,/não está fornecendo o progresso/);
});

test('upload polling tolerates initial registration race',async()=>{
  let polls=0;
  const ui=app(async()=>++polls===1?response({error:'Job not found'},404):response({status:'done',progress:100,stage:'Pronto'}));
  await ui.run("watchUpload('new',state=>progress(state.progress,state.stage,'Upload'),new AbortController().signal)");
  assert.equal(polls,2);
  assert.equal(ui.get('progress-detail').textContent,'Pronto');
});

test('missing render job stops polling and explains how to recover',async()=>{
  let polls=0;
  const ui=app(async(url)=>url==='/api/render'?response({job:'missing'}):(polls++,response({error:'Job not found'},404)));
  ui.run("current={id:'one'};");
  await ui.run("render('full')");
  assert.equal(polls,1);
  assert.match(ui.get('progress-detail').textContent,/Reabra as fotos/);
  assert.equal(ui.get('task-progress').dataset.state,'error');
});

test('server restart invalidates photos from a previous session',async()=>{
  let renders=0;
  const ui=app(async()=>{renders++;return response({});});
  ui.run("current={id:'one',serverSession:'previous-session'};");
  await ui.run("render('full')");
  assert.equal(renders,0);
  assert.match(ui.get('progress-detail').textContent,/servidor foi reiniciado/);
  assert.equal(ui.get('render').disabled,false);
});

test('timing UI formats elapsed and approximate remaining without percent extrapolation',()=>{
  const ui=app(async()=>response({}));
  ui.run("progress(20,'Revelando filme','Renderização',{elapsed_seconds:65,remaining_seconds:125,eta_state:'estimated'})");
  assert.equal(ui.get('progress-timing').hidden,false);
  assert.equal(ui.get('elapsed-time').textContent,'Decorrido: 1 min 5 s');
  assert.equal(ui.get('remaining-time').textContent,'Restante: aprox. 2 min 5 s');
  ui.run("progress(90,'Gravando TIFF','Renderização',{elapsed_seconds:200,remaining_seconds:null,eta_state:'recalculating'})");
  assert.equal(ui.get('remaining-time').textContent,'Recalculando estimativa…');
});

test('first render learns without claiming remaining time and upload clears stale timing',()=>{
  const ui=app(async()=>response({}));
  ui.run("progress(80,'Digitalizando','Renderização',{elapsed_seconds:20,remaining_seconds:null,eta_state:'learning'})");
  assert.equal(ui.get('remaining-time').textContent,'Calculando estimativa…');
  ui.run("finishProgress('Concluído')");
  assert.equal(ui.get('remaining-time').textContent,'Concluído');
  ui.run("progress(0,'Lendo imagem','Importação')");
  assert.equal(ui.get('progress-timing').hidden,true);
});

test('timing marks failure and keeps display loading distinct from backend completion',()=>{
  const ui=app(async()=>response({}));
  ui.run("updateTiming({status:'done',elapsed_seconds:30,eta_state:'displaying'})");
  assert.equal(ui.get('remaining-time').textContent,'Carregando visualização…');
  ui.run("finishProgress('Falhou',true)");
  assert.equal(ui.get('remaining-time').textContent,'Estimativa indisponível');
  assert.equal(ui.run('formatDuration(3661)'),'1 h 1 min');
});

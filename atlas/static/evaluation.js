(() => {

 const el=id=>document.getElementById(id);

 let runs=[],cohortRuns=[],detail=null,loadVersion=0,detailVersion=0,compareVersion=0,questionPage=0;

 const fmt=value=>value==null?'—':Number(value).toFixed(3);

 const pct=value=>value==null?'—':(value*100).toFixed(1)+'%';

 const ms=value=>value==null?'—':Math.round(value)+' ms';

 const label=r=>r.routing?'Selected router':r.config.name==='baseline'?'Vector baseline':r.config.name;

 const date=r=>new Date(r.started_at).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});

 const node=(tag,text,className)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(className)n.className=className;return n;};

 function clear(){loadVersion++;detailVersion++;compareVersion++;runs=[];cohortRuns=[];detail=null;el('eval-content').hidden=true;el('run-detail').hidden=true;el('run-rows').replaceChildren();el('question-rows').replaceChildren();el('comparison').replaceChildren();el('history-chart').replaceChildren();el('cohort').replaceChildren();}

 async function load(){

  const version=++loadVersion;el('eval-status').textContent='Loading measured evaluation runs…';

  try{

   const data=await window.atlasFetch('/api/evaluations');if(version!==loadVersion)return;runs=data.runs;

   if(!runs.length){el('eval-content').hidden=true;el('eval-status').textContent='No published evaluation runs yet. Run the release evaluation from the project to start this history.';return;}

   const cohorts=new Map();for(const run of runs)if(!cohorts.has(run.cohort_id))cohorts.set(run.cohort_id,run);

   const previous=el('cohort').value;el('cohort').replaceChildren(...[...cohorts].map(([id,r])=>new Option(`${r.split==='test'?'Held-out':r.split==='dev'?'Development':r.split} · ${r.summary.queries} questions · ${r.protocol.startsWith('atlas-investigation')?'Investigation '+r.protocol.split('-').at(-1):r.generation} · ${id.slice(0,6)}`,id)));

   if(cohorts.has(previous))el('cohort').value=previous;

   el('eval-status').textContent='Every value below comes from a saved evaluation run.';el('eval-content').hidden=false;renderCohort();

  }catch(error){if(version!==loadVersion)return;el('eval-content').hidden=true;el('eval-status').textContent=error.message;}

 }

 function renderCohort(){

  detailVersion++;compareVersion++;detail=null;el('run-detail').hidden=true;

  cohortRuns=runs.filter(r=>r.cohort_id===el('cohort').value).sort((a,b)=>a.started_at.localeCompare(b.started_at));

  if(!cohortRuns.length)return;

  const latest=cohortRuns.at(-1),s=latest.summary;

  const investigation=latest.protocol.startsWith('atlas-investigation-evidence');
  el('chart-metric').value=investigation?'recall':'mrr';
  el('cohort-info').textContent=`${s.answerable} answerable / ${s.queries} total · Corpus ${latest.corpus_sha256.slice(0,8)} · ${investigation?'Investigation: first five cited documents; small synthetic test':'Document retrieval: matching question set'}`;
  if(investigation)el('eval-status').textContent='Investigation cohort: citation-order metrics, not the original retrieval benchmark. Full evidence coverage: '+pct(s.evidence_recall)+'.';
  else el('eval-status').textContent='Every value below comes from a saved evaluation run.';

  el('metric-cards').replaceChildren();

  for(const [title,value,caption,warning] of [['MRR@5',fmt(s.mrr),'How early relevant evidence appears',false],['Recall@5',pct(s.recall),'Relevant documents found in the top five',false],['Citation relevance',pct(s.citation_accuracy),'Label-based relevance · needs review',true],['Search latency · p95',ms(s.retrieval_p95_ms),'Measured locally · warm model sessions',false]]){

   const card=node('div',null,'metric');card.append(node('label',title),node('strong',value),node('small',caption,warning?'warning':null));el('metric-cards').append(card);

  }

  el('history-caption').textContent=`${cohortRuns.length} measured runs · Latest: ${label(latest)}`;

  el('run-count').textContent=cohortRuns.length+' runs';

  el('run-rows').replaceChildren();

  for(const r of [...cohortRuns].reverse()){

   const tr=node('tr');tr.dataset.run=r.id;const name=node('td');const button=node('button',label(r));button.addEventListener('click',()=>inspect(r.id));name.append(button,node('small',date(r)));tr.append(name);

   for(const v of [fmt(r.summary.mrr),pct(r.summary.recall),fmt(r.summary.ndcg),pct(r.summary.citation_accuracy),ms(r.summary.retrieval_p95_ms)])tr.append(node('td',v));el('run-rows').append(tr);

  }

  for(const id of ['compare-before','compare-after'])el(id).replaceChildren(...cohortRuns.map(r=>new Option(`${label(r)} · ${date(r)}`,r.id)));

  el('compare-before').value=cohortRuns[0].id;el('compare-after').value=latest.id;

  renderChart();compare();

 }

 function renderChart(){

  const metric=el('chart-metric').value,points=cohortRuns.filter(r=>r.summary[metric]!=null),ns='http://www.w3.org/2000/svg';

  el('history-chart').replaceChildren();if(!points.length){el('history-chart').textContent='This metric was not measured for this cohort.';return;}

  function svgNode(tag,attrs,text){const n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;return n;}

  const svg=svgNode('svg',{viewBox:'0 0 640 245',role:'img','aria-label':`${el('chart-metric').selectedOptions[0].text} across ${points.length} actual runs. Values available in the run table.`});

  for(const tick of [0,.25,.5,.75,1]){const y=202-tick*160;svg.append(svgNode('line',{x1:44,x2:606,y1:y,y2:y,stroke:'#e5ebe0','stroke-dasharray':'3 4'}),svgNode('text',{x:5,y:y+4,fill:'#92a089','font-size':10},tick.toFixed(2)));}

  const coordinates=points.map((r,i)=>({x:points.length===1?325:54+i*540/(points.length-1),y:202-r.summary[metric]*160,r}));

  svg.append(svgNode('polyline',{points:coordinates.map(p=>`${p.x},${p.y}`).join(' '),fill:'none',stroke:'#44815c','stroke-width':2.5,'stroke-linejoin':'round'}));

  coordinates.forEach(({x,y,r},i)=>{const circle=svgNode('circle',{cx:x,cy:y,r:5,fill:'#fff',stroke:'#44815c','stroke-width':2});circle.append(svgNode('title',{},`${date(r)} · ${label(r)} · ${fmt(r.summary[metric])}`));svg.append(circle);if(points.length<=8||i===0||i===points.length-1)svg.append(svgNode('text',{x,y:226,'text-anchor':'middle',fill:'#84947d','font-size':10},`Run ${i+1}`));});

  el('history-chart').append(svg);

 }

 async function compare(){

  const version=++compareVersion,before=el('compare-before').value,after=el('compare-after').value;

  el('comparison').replaceChildren();

  if(before===after){el('comparison').append(node('p','Choose two different runs to compare.','compare-message'));return;}

  try{

   const data=await window.atlasFetch('/api/evaluations/compare?'+new URLSearchParams({before,after}));if(version!==compareVersion)return;

   el('comparison').append(node('p',data.regressions.length?'Quality regression detected: '+data.regressions.join(', '):'No quality drop greater than 0.02 in the compared metrics.','compare-message'));

   for(const [key,title] of [['mrr','MRR@5'],['recall','Recall@5'],['citation_accuracy','Citation relevance'],['retrieval_p95_ms','Search p95']]){

    const delta=data.deltas[key];if(delta==null)continue;const row=node('div',null,'delta');const value=node('b',(delta>0?'+':'')+delta.toFixed(key==='retrieval_p95_ms'?1:3)+(key==='retrieval_p95_ms'?' ms':''));

    if(key==='retrieval_p95_ms'?delta>0:delta<0)value.className='negative';row.append(node('span',title),value);el('comparison').append(row);

   }

   const improved=data.questions.filter(q=>q.delta>0).length,worse=data.questions.filter(q=>q.delta<0).length;

   el('comparison').append(node('p',`${improved} questions improved in MRR; ${worse} worsened. Timing changes are observational, not significance tests.`,'compare-message'));

  }catch(error){if(version===compareVersion)el('comparison').textContent=error.message;}

 }

 async function inspect(id){

  const version=++detailVersion;el('run-detail').hidden=false;el('run-title').textContent='Loading run…';el('question-rows').replaceChildren();el('run-config').textContent='';el('run-meta').textContent='';detail=null;el('download-run').disabled=true;

  try{

   const r=await window.atlasFetch('/api/evaluations/'+encodeURIComponent(id));if(version!==detailVersion)return;detail=r;

   el('run-title').textContent=label(r);el('run-meta').textContent=date(r)+' · '+r.id;

   el('run-config').textContent=`${r.protocol} · Code ${r.code_sha256.slice(0,12)} · ${r.config.chunking} chunks · Hybrid ${r.config.hybrid?'on':'off'} · Reranker ${r.config.rerank?'on':'off'} · Router ${r.routing?'on':'off'} · Graph routing ${r.graph_enabled?'on':'off'} · Answer mode ${r.generation}. Corpus ${r.corpus_sha256.slice(0,12)}. Question set ${r.questions_sha256.slice(0,12)}. Local API spend: $${r.summary.api_cost_usd.toFixed(2)} per query; compute cost unmeasured.`;

   questionPage=0;el('question-search').value='';el('failures-only').checked=false;renderQuestions();

   document.querySelectorAll('#run-rows tr').forEach(tr=>tr.classList.toggle('selected-run',tr.dataset.run===id));el('download-run').disabled=false;

   el('run-detail').scrollIntoView({behavior:'smooth',block:'start'});

  }catch(error){if(version===detailVersion)el('run-title').textContent=error.message;}

 }

 function renderQuestions(){

  if(!detail)return;

  const needle=el('question-search').value.toLowerCase();

  const rows=[...detail.rows].filter(r=>r.query.toLowerCase().includes(needle)&&(!el('failures-only').checked||(r.recall==null?!r.answer.abstained:r.recall<1||r.mrr<1))).sort((a,b)=>(a.mrr??-1)-(b.mrr??-1));

  questionPage=Math.min(questionPage,Math.max(0,Math.ceil(rows.length/15)-1));

  const start=questionPage*15;el('question-rows').replaceChildren();

  for(const row of rows.slice(start,start+15)){

   const tr=node('tr'),question=node('td');question.append(node('span',row.query),node('small',row.category));

   const evidence=node('td'),details=node('details'),summary=node('summary',row.answer.abstained?'Abstained':'Inspect sources');

   const body=node('p',`Expected: ${row.relevant.join(', ')||'No answer'}. Retrieved: ${row.ranked.join(', ')||'None'}. Answer: ${row.answer.answer}`);

   details.append(summary,body);evidence.append(details);tr.append(question,node('td',fmt(row.mrr)),node('td',pct(row.recall)),evidence);el('question-rows').append(tr);

  }

  el('question-page-label').textContent=rows.length?`${start+1}–${Math.min(start+15,rows.length)} of ${rows.length}`:'No matching questions';

  el('questions-prev').disabled=questionPage===0;el('questions-next').disabled=start+15>=rows.length;

 }

 el('question-search').addEventListener('input',()=>{questionPage=0;renderQuestions();});

 el('failures-only').addEventListener('change',()=>{questionPage=0;renderQuestions();});

 el('questions-prev').addEventListener('click',()=>{questionPage--;renderQuestions();});

 el('questions-next').addEventListener('click',()=>{questionPage++;renderQuestions();});

 el('download-run').addEventListener('click',()=>{if(!detail)return;const url=URL.createObjectURL(new Blob([JSON.stringify(detail,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=detail.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

 el('cohort').addEventListener('change',renderCohort);el('chart-metric').addEventListener('change',renderChart);el('refresh-runs').addEventListener('click',load);el('compare-before').addEventListener('change',compare);el('compare-after').addEventListener('change',compare);

 window.atlasEvaluations={load,clear};

})();


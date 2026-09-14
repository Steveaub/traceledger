const $ = id => document.getElementById(id);
let currentAnswer = '', requestSequence = 0, currentController;
let investigationMode = false;
function setExperience(investigate) {
  investigationMode = investigate;
  $('quick-mode').setAttribute('aria-pressed',String(!investigate));
  $('investigate-mode').setAttribute('aria-pressed',String(investigate));
  $('experience-note').textContent=investigate?'Follow records and conversation threads. Up to six actions; exact cited excerpts.':'Find supporting passages with the measured retrieval default.';
  $('mode').disabled=investigate; $('generation').disabled=investigate;
  if (!$('submit').disabled) $('submit').textContent=investigate?'Investigate ↗':'Find evidence ↗';
}
$('quick-mode').addEventListener('click',()=>setExperience(false));
$('investigate-mode').addEventListener('click',()=>setExperience(true));
async function loadFeeds() {
  $('feed-status').textContent='Loading source inventory…';
  try {
    const data=await window.atlasFetch('/api/feeds');
    $('feed-status').replaceChildren();
    data.sources.forEach(source=>{
      const p=document.createElement('p');p.textContent=`${source.label}: ${source.records} accessible records · ${source.demo_records} fictional · ${source.status}`;$('feed-status').append(p);
    });
  } catch(error) {$('feed-status').textContent=error.message;}
}
function renderInvestigation(data) {
  const root=$('investigation-trail');root.replaceChildren();root.hidden=!data.investigation;
  if(!data.investigation)return;
  const run=data.investigation;
  const heading=document.createElement('h3');heading.textContent=run.status==='needs_review'?'Investigation · review needed':'Investigation · evidence found';root.append(heading);
  const subtitle=document.createElement('p');subtitle.className='trace-caption';subtitle.textContent=`${run.steps.length} of ${run.max_actions} actions · Selected, accessible sources only`;root.append(subtitle);
  const about=document.createElement('details');const aboutTitle=document.createElement('summary');aboutTitle.textContent='How this investigation works';const aboutText=document.createElement('p');aboutText.textContent=run.policy+'. Source evidence guides each follow-up; the system does not send messages or change records.';about.append(aboutTitle,aboutText);root.append(about);
  const list=document.createElement('ol');
  run.steps.forEach(step=>{
    const li=document.createElement('li');const details=document.createElement('details');const title=document.createElement('summary');
    title.textContent=`${step.label} · ${step.source_ids.length} records`;details.append(title);
    const info=document.createElement('p');info.textContent=(step.query?step.query+' · ':'')+Math.round(step.duration_ms)+'ms';details.append(info);
    const ids=document.createElement('p');ids.textContent=step.source_ids.join(', ')||'No supporting records';details.append(ids);li.append(details);list.append(li);
  });root.append(list);
  [...run.gaps,...run.caveats].forEach(text=>{const p=document.createElement('p');p.className='investigation-gap';p.textContent=text;root.append(p);});
}
window.atlasHeaders = () => { const headers = {'Content-Type':'application/json'}; if ($('token').value) headers.Authorization = 'Bearer ' + $('token').value; return headers; };
window.atlasFetch = async (url, options={}) => {
  const response = await fetch(url, {...options, headers:window.atlasHeaders()});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your question and access settings.');
  return data;
};
function switchView(name) {
  window.atlasVoice.stop();
  for (const view of ['workspace','evaluation']) {
    $(view+'-view').hidden = view !== name;
    $('nav-'+view).classList.toggle('active', view === name);
    if (view === name) $('nav-'+view).setAttribute('aria-current','page');
    else $('nav-'+view).removeAttribute('aria-current');
  }
  $('breadcrumb').textContent = name === 'workspace' ? 'Workspace / Evidence' : 'Workspace / Evaluation lab';
  history.replaceState(null, '', '#'+name);
  document.title='TraceLedger · '+(name==='evaluation'?'Evaluation lab':'Evidence workspace');
  if (name === 'evaluation') window.atlasEvaluations.load();
  document.getElementById('main').scrollIntoView({block:'start'});
}
$('nav-workspace').addEventListener('click',()=>switchView('workspace'));
$('nav-evaluation').addEventListener('click',()=>switchView('evaluation'));
async function loadProjects() {
  try {
    const data = await window.atlasFetch('/api/projects');
    const options = [new Option('All accessible projects',''),new Option('Public references only','public')];
    data.projects.forEach(id=>options.push(new Option(data.names?.[id] || id,id)));
    $('project').replaceChildren(...options);
    $('project-count').textContent = `${data.projects.length} accessible projects`;
  } catch (error) { $('project-count').textContent = 'Sign in to search'; $('status').textContent = error.message; }
}
$('reconnect').addEventListener('click',()=>{
  requestSequence++; currentController?.abort(); window.atlasVoice.reset(); currentAnswer='';
  $('answer').replaceChildren(); $('citations').replaceChildren(); $('graph').replaceChildren();
  $('paths').hidden=true; $('answer-notes').hidden=true; $('source-count').textContent='0';
  $('investigation-trail').hidden=true; $('investigation-trail').replaceChildren(); loadFeeds();
  $('copy-answer').disabled=true; $('submit').disabled=false; $('submit').textContent='Find evidence ↗';
  $('answer-card').setAttribute('aria-busy','false');
  window.atlasEvaluations.clear(); loadProjects();
  if (!$('evaluation-view').hidden) window.atlasEvaluations.load();
});
document.querySelectorAll('.scenario').forEach(button=>button.addEventListener('click',()=>{
  setExperience(button.dataset.investigate==='true');
  $('question').value=button.dataset.query; $('question').focus();
}));
$('question').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();$('ask').requestSubmit();}});
function renderAnswer(text,visibleLines=2) {
  $('answer').replaceChildren();
  const lines=text.split('\n').filter(Boolean);
  const extra=document.createElement('details'); extra.className='answer-extra';
  const summary=document.createElement('summary'); summary.textContent=`Show ${Math.max(0,lines.length-visibleLines)} more evidence excerpts`; extra.append(summary);
  lines.forEach((line,index)=>{
    const p=document.createElement('p');p.className='answer-line';
    line.split(/(\[\d+\])/g).forEach(part=>{
      const match=part.match(/^\[(\d+)\]$/);
      if(!match){p.append(document.createTextNode(part));return;}
      const button=document.createElement('button');button.className='cite-ref';button.textContent=part;button.setAttribute('aria-label','Go to source '+match[1]);
      button.addEventListener('click',()=>{const target=$('source-'+match[1]);if(target){target.closest('details').open=true;target.scrollIntoView({behavior:'smooth',block:'center'});target.focus({preventScroll:true});}});p.append(button);
    });
    (index<visibleLines?$('answer'):extra).append(p);
  });
  if(lines.length>visibleLines)$('answer').append(extra);
}
function renderEvidence(data) {
  $('citations').replaceChildren();
  const groups=new Map();
  data.citations.forEach(c=>{if(!groups.has(c.doc_id))groups.set(c.doc_id,[]);groups.get(c.doc_id).push(c);});
  $('source-count').textContent=groups.size;
  if(!groups.size){const p=document.createElement('p');p.className='chart-note';p.textContent='No supporting sources found. Try a specific project name, incident ID, or a narrower question.';$('citations').append(p);}
  [...groups.values()].forEach((citations,index)=>{
    const first=citations[0],details=document.createElement('details');details.className='source-card';details.id='source-'+first.id;details.tabIndex=-1;details.open=index===0;
    const summary=document.createElement('summary');const tag=document.createElement('span');tag.className='source-tag';tag.textContent=first.synthetic?'FICTIONAL PROJECT RECORD':first.source.startsWith('upload:')?'IMPORTED RECORD':'SOURCE RECORD';
    const title=document.createElement('span');title.className='source-title';title.textContent=first.title;summary.append(tag,title);details.append(summary);
    citations.forEach(c=>{const quote=document.createElement('blockquote');quote.textContent=`[${c.id}] ${c.quote}`;if(c.id!==first.id){quote.id='source-'+c.id;quote.tabIndex=-1;}details.append(quote);});
    const metadata=document.createElement('p');metadata.textContent=first.channel && first.channel!=='documents'?`${first.channel.toUpperCase()} · ${first.author || 'Unknown sender'} · ${first.date} · ${first.decision_status}`:first.doc_id;details.append(metadata);
    const full=document.createElement('button');full.className='quiet full-record';full.textContent='Read full record';
    full.addEventListener('click',async()=>{
      full.disabled=true;
      try {const record=await window.atlasFetch('/api/source/'+encodeURIComponent(first.doc_id));
        const body=document.createElement('p');body.className='full-record-body';body.textContent=record.text;details.append(body);full.remove();
      } catch(error){full.disabled=false;full.textContent=error.message;}
    });details.append(full);
    if(first.source.startsWith('https://')){const link=document.createElement('a');link.href=first.source;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open original document ↗';details.append(link);}
    $('citations').append(details);
  });
  $('paths').hidden=!data.graph_paths.length;$('graph').replaceChildren();
  const seen=new Set();data.graph_paths.forEach(edge=>{
    const key=[edge.source,edge.relation,edge.target,edge.doc_id].join('|');if(seen.has(key))return;seen.add(key);
    const div=document.createElement('div');div.className='graph-edge';div.textContent=`${edge.source} → ${edge.relation} → ${edge.target}`;
    const small=document.createElement('small');small.textContent='Source: '+edge.doc_id;div.append(small);$('graph').append(div);
  });
}
$('ask').addEventListener('submit',async event=>{
  event.preventDefault();if($('submit').disabled)return;
  const sources=[...document.querySelectorAll('#feed-options input:checked')].map(el=>el.value);
  if(!sources.length){$('status').textContent='Choose at least one source to search.';$('status').classList.add('error');return;}
  const sequence=++requestSequence;const controller=new AbortController();currentController=controller;const started=performance.now();
  window.atlasVoice.reset();currentAnswer='';$('copy-answer').disabled=true;
  $('submit').disabled=true;$('submit').textContent='Finding evidence…';$('answer-card').setAttribute('aria-busy','true');
  $('status').classList.remove('error');$('status').textContent='Searching accessible records and preparing source passages…';
  $('answer').replaceChildren();for(let i=0;i<3;i++){const skeleton=document.createElement('div');skeleton.className='skeleton';$('answer').append(skeleton);}
  $('citations').replaceChildren();$('source-count').textContent='0';$('graph').replaceChildren();$('paths').hidden=true;$('answer-notes').hidden=true;
  $('investigation-trail').hidden=true;
  if(investigationMode){$('submit').textContent='Investigating…';$('status').textContent='Following accessible evidence and checking conversation context…';}
  const timeout=setTimeout(()=>controller.abort(),90000);
  try {
    const data=await window.atlasFetch('/api/query',{method:'POST',signal:controller.signal,body:JSON.stringify({query:$('question').value,project:$('project').value||null,mode:investigationMode?'investigate':$('mode').value,generation:$('generation').value,sources})});
    if(sequence!==requestSequence)return;
    const duration=(performance.now()-started)/1000;
    $('status').textContent=`${data.abstained?'Insufficient evidence':'Evidence retrieved'} · ${duration.toFixed(2)}s request · ${data.cached?'cached answer':Math.round(data.retrieval_ms)+'ms search'} · ${new Set(data.citations.map(c=>c.doc_id)).size} sources`;
    currentAnswer=data.answer;renderAnswer(data.answer,data.investigation?3:2);renderEvidence(data);window.atlasVoice.setAnswer(data.answer);$('copy-answer').disabled=false;
    renderInvestigation(data);
    $('answer-notes').hidden=false;$('answer-notes').textContent=data.abstained?'The accessible records do not provide enough evidence. No answer was invented.':data.generation_mode==='extractive_evidence'?'Exact source excerpts. Check the full evidence trail before making a decision.':'Local AI answer with literal evidence validation. Additional evidence may exist; review the source trail.';
    if(data.investigation)$('answer-notes').textContent='Evidence-driven retrieval with exact excerpts. Message status is source metadata, not independent verification of authority. Review gaps and original records before acting.';
  } catch(error) {
    if(sequence!==requestSequence)return;
    $('answer').replaceChildren();$('status').classList.add('error');$('status').textContent=error.name==='AbortError'?'The request timed out. Your question is saved—please try again.':error.message;
  } finally {clearTimeout(timeout);if(sequence===requestSequence){$('submit').disabled=false;setExperience(investigationMode);$('answer-card').setAttribute('aria-busy','false');}}
});
$('copy-answer').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(currentAnswer);$('copy-answer').textContent='Copied';setTimeout(()=>{$('copy-answer').textContent='Copy';},1600);}catch(_){$('status').textContent='Copy is unavailable. Select the answer text to copy it.';}});
loadProjects();
loadFeeds();

window.addEventListener('DOMContentLoaded',()=>{if(location.hash==='#evaluation')switchView('evaluation');});
window.addEventListener('hashchange',()=>switchView(location.hash==='#evaluation'?'evaluation':'workspace'));

async function initializeHostedDemo() {
  try {
    const health = await window.atlasFetch('/health');
    if (!health.hosted_demo || requestSequence || $('question').value.trim() || location.hash === '#evaluation') return;
    $('generation').replaceChildren(new Option('Verified source excerpts', 'evidence'));
    $('question').value = 'Investigate Project Alpha: why was commissioning delayed, who approved the change, and was the schedule updated?';
    setExperience(true);
    $('ask').requestSubmit();
  } catch (_) { /* Existing connection feedback handles an unavailable server. */ }
}
initializeHostedDemo();

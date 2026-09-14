const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(supported=true){
 const elements={};
 for(const id of ['microphone','question','voice-status','speech-status','read-aloud'])elements[id]={value:'',textContent:'',disabled:false,events:{},addEventListener(n,f){this.events[n]=f},setAttribute(n,v){this[n]=v}};
 const sessions=[],spoken=[];
 class Recognition{constructor(){sessions.push(this)}start(){}stop(){this.onend()}abort(){this.aborted=true}}
 const synth={cancel(){},getVoices(){return [{localService:true,lang:'en-US'}]},speak(u){spoken.push(u)}};
 const window={SpeechRecognition:supported?Recognition:undefined,speechSynthesis:synth,SpeechSynthesisUtterance:class{},addEventListener(){}};
 vm.runInNewContext(fs.readFileSync('atlas/static/voice.js','utf8'),{window,document:{getElementById:id=>elements[id],querySelectorAll:()=>[]},SpeechSynthesisUtterance:class{constructor(text){this.text=text}}});
 return {elements,window,sessions,spoken};
}
test('dictation preserves existing text, caps input, and never submits',()=>{
 const {elements:e,sessions:s}=setup();e.question.value='Existing';e.microphone.events.click();
 s[0].onresult({results:[[{transcript:'dictated question'}]]});assert.equal(e.question.value,'Existing dictated question');
 s[0].onresult({results:[[{transcript:'a'.repeat(1100)}]]});assert.equal(e.question.value.length,1000);
 s[0].onend();assert.equal(e.question.readOnly,false);assert.equal(e.microphone['aria-label'],'Speak your question');assert.equal(e.microphone['aria-pressed'],'false');
});
test('late recognition result cannot overwrite a submitted question',()=>{
 const {elements:e,sessions:s,window:w}=setup();e.microphone.events.click();w.atlasVoice.reset();e.question.value='New question';
 s[0].onresult({results:[[{transcript:'old'}]]});assert.equal(e.question.value,'New question');assert.equal(s[0].aborted,true);
});
test('unsupported browser has usable text fallback',()=>{const {elements:e}=setup(false);assert.equal(e.microphone.disabled,true);assert.match(e['voice-status'].textContent,/Windows/)});
test('speech reads citation numbers and stop cancels queued utterances',()=>{
 const {elements:e,window:w,spoken}=setup();w.atlasVoice.setAnswer('Approved [2]. Next sentence.');e['read-aloud'].events.click();assert.match(spoken[0].text,/source 2/);
 e['read-aloud'].events.click();spoken[0].onend();assert.equal(spoken.length,1);assert.equal(e['read-aloud'].disabled,false);
});
test('remote-only voice is not selected',()=>{const {elements:e,window:w,spoken}=setup();w.speechSynthesis.getVoices=()=>[{localService:false,lang:'en-US'}];w.atlasVoice.setAnswer('Private response');e['read-aloud'].events.click();assert.equal(spoken.length,0);assert.match(e['speech-status'].textContent,/No local English voice/)});

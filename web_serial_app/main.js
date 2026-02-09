// Web Serial app implementing similar features to the desktop app
let port = null;
let reader = null;
let writer = null;
let keepReading = false;
let lastCaret = { normal: 0, berry: 0 };

const btnRequest = document.getElementById('btn-request-port');
const btnConnect = document.getElementById('btn-connect');
const connStatus = document.getElementById('conn-status');
const baudSelect = document.getElementById('baud-select');
const statusMessage = document.getElementById('status-message');
const serialOutput = document.getElementById('serial-output');
const editorNormal = document.getElementById('editor-normal');
const editorBerry = document.getElementById('editor-berry');
const tabs = document.querySelectorAll('.tab');
const btnSendLine = document.getElementById('btn-send-line');
const btnSendAll = document.getElementById('btn-send-all');
const btnClear = document.getElementById('btn-clear');
const btnOpen = document.getElementById('btn-open');
const fileInput = document.getElementById('file-input');

function setStatus(msg, color='black'){
  statusMessage.textContent = msg;
  statusMessage.style.color = color;
}

function appendOutput(text){
  serialOutput.value += text + '\n';
  serialOutput.scrollTop = serialOutput.scrollHeight;
}

async function requestPort(){
  try{
    const requested = await navigator.serial.requestPort();
    port = requested;
    setStatus('Port selected');
    try{ btnRequest.textContent = 'Port selected'; }catch(e){}
  }catch(e){
    setStatus('Port selection canceled', 'orange');
  }
}

async function connect(){
  if(!port){
    setStatus('No port selected', 'red');
    return;
  }
  const baud = Number(baudSelect.value);
  try{
    await port.open({baudRate: baud});
    writer = port.writable.getWriter();
    setStatus(`Connected @ ${baud}`,'green');
    try{ btnConnect.textContent = 'Disconnect'; }catch(e){}
    connStatus.textContent = 'Connected'; connStatus.classList.add('connected'); connStatus.classList.remove('disconnected');
    keepReading = true;
    readLoop();
    // save baud
    localStorage.setItem('last_baud', baud);
  }catch(e){
    setStatus('Failed to open port: ' + e.message, 'red');
  }
}

async function disconnect(){
  keepReading = false;
  try{
    if(reader){
      try{ await reader.cancel(); }catch(e){}
      reader = null;
    }
    if(writer){ writer.releaseLock(); writer = null; }
    if(port){ await port.close(); }
  }catch(e){ console.error(e); }
  port = null;
  connStatus.textContent = 'Disconnected'; connStatus.classList.remove('connected'); connStatus.classList.add('disconnected');
  setStatus('Disconnected');
  try{ btnRequest.textContent = 'Select Port'; }catch(e){}
  try{ btnConnect.textContent = 'Connect'; }catch(e){}
}

async function readLoop(){
  try{
    const textDecoder = new TextDecoderStream();
    const readableStreamClosed = port.readable.pipeTo(textDecoder.writable);
    reader = textDecoder.readable.getReader();
    while(keepReading){
      const {value, done} = await reader.read();
      if(done) break;
      if(value) appendOutput(value.trim());
    }
  }catch(e){
    appendOutput('Read error: ' + e);
  }
}

function getActiveEditor(){
  // Prefer the focused editor (so Ctrl+Enter works even if tab classes are out of sync)
  const ae = document.activeElement;
  if(ae && ae.tagName === 'TEXTAREA' && ae.classList.contains('editor')) return ae;
  return document.querySelector('.editor.active');
}

function _getLineBounds(editor){
  const pos = editor.selectionStart;
  const text = editor.value.replace(/\r/g,'');
  const before = text.slice(0, pos);
  const lineStart = before.lastIndexOf('\n') + 1;
  const lineEndIdx = text.indexOf('\n', pos);
  const endIdx = lineEndIdx === -1 ? text.length : lineEndIdx;
  return {start: lineStart, end: endIdx};
}

function highlightCurrentLineTemporarily(editor, ms=700){
  try{
    const startSel = editor.selectionStart;
    const endSel = editor.selectionEnd;
    const bounds = _getLineBounds(editor);
    // select the line
    editor.focus();
    editor.setSelectionRange(bounds.start, bounds.end);
    // restore after timeout
    setTimeout(()=>{
      try{ editor.setSelectionRange(startSel, endSel); editor.focus(); }catch(e){}
    }, ms);
  }catch(e){ /* ignore */ }
}

function getSelectedTextOrLine(){
  const editor = getActiveEditor();
  // editor is a textarea; try using selectionStart/End, otherwise fall back to lastCaret
  let start = editor.selectionStart;
  let end = editor.selectionEnd;
  const tab = editor.id === 'editor-berry' ? 'berry' : 'normal';
  if(typeof start !== 'number' || typeof end !== 'number'){
    const p = lastCaret[tab] || 0;
    start = end = p;
  } else if(start === end && start === 0 && lastCaret[tab] && lastCaret[tab] > 0){
    // sometimes the browser reports 0 even when caret moved — use last known caret
    start = end = lastCaret[tab];
  }
  if(start !== end){
    return editor.value.slice(start, end);
  }
  const text = editor.value.replace(/\r/g,'');
  const before = text.slice(0, start);
  const lineStart = before.lastIndexOf('\n') + 1;
  const lineEndIdx = text.indexOf('\n', start);
  const endIdx = lineEndIdx === -1 ? text.length : lineEndIdx;
  return text.slice(lineStart, endIdx);
}

async function sendTextLines(text){
  if(!port || !port.writable){ setStatus('Not connected', 'red'); return; }
  // clear output
  serialOutput.value = '';
  const lines = text.split(/\r?\n/).filter(l => l.trim().length>0);
  for(const line of lines){
    const data = new TextEncoder().encode(line + '\n');
    await writer.write(data);
  }
  setStatus(`Sent ${lines.length} line(s)`);
}

async function sendSelectedOrLine(){
  const activeTab = document.querySelector('.tab.active').dataset.tab;
  const editor = getActiveEditor();
  const rawText = getSelectedTextOrLine();
  console.log('sendSelectedOrLine:', {activeTab, editorId: editor?.id, rawText, caretPos: editor?.selectionStart});
  if(!rawText || rawText.trim().length===0){ setStatus('Line is empty', 'orange'); return; }
  // highlight the current line(s) briefly
  try{ highlightCurrentLineTemporarily(editor); }catch(e){}
  let text = rawText;
  if(activeTab === 'berry'){
    // prefix each non-empty line
    text = text.split(/\r?\n/).map(l=> l.trim()?('br '+l):'').join('\n');
    console.log('Berry mode applied:', {before: rawText, after: text});
  }
  await sendTextLines(text);
}

async function sendAllLines(){
  const activeTab = document.querySelector('.tab.active').dataset.tab;
  const editor = getActiveEditor();
  const text = editor.value.replace(/\r/g,'');
  if(!text || text.trim().length===0){ setStatus('Text area is empty','orange'); return; }
  let out = text;
  if(activeTab === 'berry'){
    out = text.split('\n').map(l=> l.trim()?('br '+l):'').join('\n');
  }
  await sendTextLines(out);
}

function switchTab(tab){
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active', b.dataset.tab===tab));
  document.querySelectorAll('.editor').forEach(e=>e.classList.toggle('active', e.id=== 'editor-'+tab));
}

// keyboard shortcuts
window.addEventListener('keydown', async (e)=>{
  if((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'A' || e.key === 'a')){
    e.preventDefault();
    await sendAllLines();
  }
  if((e.ctrlKey || e.metaKey) && (e.key === 'o' || e.key === 'O')){
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener('change', async (evt)=>{
  const f = evt.target.files[0];
  if(!f) return;
  const text = await f.text();
  const editor = getActiveEditor();
  editor.value = text;
  setStatus('Loaded file: ' + f.name);
});

btnRequest.addEventListener('click', requestPort);
btnConnect.addEventListener('click', async ()=>{
  if(port && port.readable){
    await disconnect();
  }else{
    await connect();
  }
});

btnSendLine.addEventListener('click', sendSelectedOrLine);
btnSendAll.addEventListener('click', sendAllLines);
btnClear.addEventListener('click', ()=>{ getActiveEditor().value=''; setStatus('Cleared'); });
btnOpen.addEventListener('click', ()=>fileInput.click());

tabs.forEach(t=>t.addEventListener('click', ()=>switchTab(t.dataset.tab)));

// initial small setup: ensure editors have a blank line
editorNormal.value = '';
editorBerry.value = '';

// Ensure Ctrl+Enter works when a textarea is focused (covers Berry mode reliably)
editorNormal.addEventListener('keydown', async (e)=>{
  if((e.ctrlKey || e.metaKey) && e.key === 'Enter'){
    e.preventDefault();
    await sendSelectedOrLine();
  }
});
editorBerry.addEventListener('keydown', async (e)=>{
  if((e.ctrlKey || e.metaKey) && e.key === 'Enter'){
    e.preventDefault();
    await sendSelectedOrLine();
  }
});

// Track caret position so we can fall back when selection info is unreliable
function _updateCaretFor(editor, key){
  return ()=>{ try{ lastCaret[key] = editor.selectionStart; }catch(e){} }
}
['click','keyup','input','blur'].forEach(ev=>{
  editorNormal.addEventListener(ev, _updateCaretFor(editorNormal,'normal'));
  editorBerry.addEventListener(ev, _updateCaretFor(editorBerry,'berry'));
});

setStatus('Ready');

// Note: Web Serial requires secure context (https or localhost) and user gesture to request port.

const root = document.querySelector('#app');
let account=null, batchId=null, pollTimer=null;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, opts={}) { const response = await fetch('/api'+path, {...opts, headers: opts.body instanceof FormData ? {} : {'Content-Type':'application/json'}}); if(!response.ok){let x=await response.json().catch(()=>({}));throw Error(typeof x.detail==='string'?x.detail:'Une erreur est survenue.')} return response.json(); }
function auth(setup) { root.innerHTML=`<div class="auth"><div class="card"><div class="brand" style="padding-left:0"><div class="mark">P</div><div><strong style="color:#173642">PROHEAT</strong><small>Saisie comptable</small></div></div><h1>${setup?'Créer l’administrateur':'Bienvenue'}</h1><p class="muted">${setup?'Première configuration locale. Choisissez un mot de passe d’au moins 8 caractères.':'Connectez-vous à votre espace de travail local.'}</p><form id="auth"><div class="field"><label for="username">Identifiant</label><input id="username" required minlength="3" maxlength="80" autocomplete="username"></div><div class="field"><label for="password">Mot de passe</label><input id="password" type="password" ${setup?'minlength="8"':''} required maxlength="128" autocomplete="${setup?'new-password':'current-password'}"></div><div id="message" class="error" role="alert"></div><button class="button">${setup?'Créer le compte':'Se connecter'}</button></form></div></div>`; document.querySelector('#auth').onsubmit=async e=>{e.preventDefault();try{const body=JSON.stringify({username:document.querySelector('#username').value,password:document.querySelector('#password').value});await api(setup?'/setup':'/login',{method:'POST',body});if(setup){auth(false);return} account=await api('/me');await render()}catch(err){document.querySelector('#message').textContent=err.message}} }

function status(message, error=false){const el=document.querySelector('#status');if(el){el.textContent=message;el.className=error?'error':'muted'}}
async function checkBatch(){
  if(!batchId)return;
  try{
    const batch=await api('/batches/'+encodeURIComponent(batchId));
    const progress=document.querySelector('#progress');progress.hidden=false;progress.max=batch.total;progress.value=batch.processed;
    if(batch.processed<batch.total){status(`Traitement : ${batch.processed} / ${batch.total} factures`);pollTimer=setTimeout(checkBatch,2000);return}
    status(`${batch.total} factures traitées. Votre fichier Excel est prêt.`);
    const link=document.querySelector('#download');link.href='/api/batches/'+encodeURIComponent(batchId)+'/invoice-data.xlsx';link.hidden=false;
    document.querySelector('#submit').disabled=false;
  }catch(e){status(e.message,true);document.querySelector('#submit').disabled=false}
}
async function render(){
  clearTimeout(pollTimer);
  root.innerHTML=`<div class="simple-app"><header class="simple-header"><div class="brand"><div class="mark">P</div><div><strong style="color:#173642">PROHEAT</strong><small>Factures → Excel</small></div></div><button class="link" id="logout">Déconnexion</button></header><main class="simple-main"><h1>Vos factures, dans Excel.</h1><p class="muted">Ajoutez vos fichiers et téléchargez le résultat. Les informations manquantes ou douteuses sont signalées en rouge dans Excel.</p><section class="card panel-body"><form id="upload"><label class="drop" style="display:block" for="files"><strong>Choisir des factures</strong><p class="muted">PDF, JPG ou PNG · 100 fichiers maximum · 10 Mo par fichier</p><input id="files" type="file" multiple accept=".pdf,.jpg,.jpeg,.png" required></label><p id="selection" class="muted"></p><button class="button" id="submit">Créer mon Excel</button></form><p id="status" role="status" aria-live="polite"></p><progress id="progress" hidden style="width:100%"></progress><p><a class="button" id="download" hidden download>Télécharger Excel</a></p></section></main></div>`;
  document.querySelector('#logout').onclick=async()=>{clearTimeout(pollTimer);await api('/logout',{method:'POST'});account=null;auth(false)};
  document.querySelector('#files').onchange=e=>{document.querySelector('#selection').textContent=`${e.target.files.length} fichier(s) sélectionné(s)`};
  document.querySelector('#upload').onsubmit=async e=>{
    e.preventDefault();const files=document.querySelector('#files').files;
    if(files.length<1||files.length>100){status('Choisissez entre 1 et 100 fichiers.',true);return}
    if([...files].some(f=>f.size>10*1024*1024)){status('Chaque fichier doit faire 10 Mo maximum.',true);return}
    clearTimeout(pollTimer);document.querySelector('#submit').disabled=true;document.querySelector('#download').hidden=true;status('Envoi des fichiers…');
    const body=new FormData();for(const file of files)body.append('files',file);
    try{const batch=await api('/batches',{method:'POST',body});batchId=batch.id;localStorage.setItem('proheat-last-batch',batchId);checkBatch()}catch(e){status(e.message,true);document.querySelector('#submit').disabled=false}
  };
  batchId=localStorage.getItem('proheat-last-batch');
  if(!batchId){try{const batches=await api('/batches');batchId=batches[0]?.id||null}catch{}}
  if(batchId)checkBatch();
}
(async()=>{try{const setup=await api('/setup-status');if(setup.needed)return auth(true);try{account=await api('/me');await render()}catch{auth(false)}}catch(e){root.textContent='Service indisponible : '+e.message}})();

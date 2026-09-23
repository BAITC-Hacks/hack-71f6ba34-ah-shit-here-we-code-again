const $ = (s) => document.querySelector(s);
let csrf = '', currentOffer = null, busy = false;
const money = n => n == null ? 'Цена не указана' : Number(n).toLocaleString('ru-RU') + ' ₸';
function el(tag, cls, text) { const node = document.createElement(tag); if (cls) node.className = cls; if (text != null) node.textContent = text; return node; }
function safeLink(url, text) { const a = el('a', '', text); try { const u = new URL(url); if (u.protocol === 'https:') { a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; } } catch {} return a; }
async function api(path, data) { const r = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(data)}); const body = await r.json(); if (!r.ok) throw new Error(body.error || 'Ошибка запроса'); return body; }
function message(text, cls='assistant') { const node = el('article','message '+cls); node.append(el('p','',text)); $('#messages').append(node); $('#messages').scrollTop = $('#messages').scrollHeight; return node; }
function card(p) {
 const node = el('div','product'); node.append(el('div','sku','АРТИКУЛ '+p.article), el('h4','',p.name),el('div','price',money(p.price)));
 node.append(el('div','stock',p.quantity == null ? 'Остаток не подтверждён' : 'Общий остаток: '+p.quantity));
 if(p.alternative){node.append(el('p','warning','Кандидат на замену для '+p.alternative.for_article),el('p','',p.alternative.matches.join('; ')),el('p','',p.alternative.differences.join('; ')),el('p','checked',p.alternative.caution));}
 for (const w of p.warnings || []) node.append(el('p','warning',w));
 const detail = el('details'); detail.append(el('summary','','Характеристики и склады'));
 if (p.description) detail.append(el('p','',p.description));
 const dl = el('dl');
 for(const [k,v] of Object.entries(p.properties || {})) { dl.append(el('dt','',k),el('dd','',Array.isArray(v)?v.join(', '):String(v))); }
 detail.append(dl);
 for (const store of p.stores || []) if(Number(store.quantity)>0) detail.append(el('p','',store.name+': '+store.quantity));
 node.append(detail);
 const certs=p.certificates || []; if(certs.length) certs.forEach((u,i)=>node.append(safeLink(u,'Сертификат '+(i+1)))); else node.append(el('p','checked','Ссылка на сертификат в доступных полях API не найдена.'));
 node.append(safeLink(p.url,'Карточка на ekt.kz ↗'), el('p','checked','Данные получены в '+p.checked_at));
 const controls=el('div','product-actions'), label=el('label','','Кол-во '), input=el('input'); input.type='number'; input.min='1'; input.step='any'; input.value='1'; input.setAttribute('aria-label','Количество для '+p.article); label.append(input);
 const button=el('button','','Подготовить добавление'); button.disabled=!(Number(p.quantity)>0); button.onclick=async()=>{ button.disabled=true; try { currentOffer=await api('/api/propose',{id:p.id,quantity:Number(input.value)}); $('#confirmation h2').textContent='Добавить в демо-корзину?';$('#accept-offer').textContent='Да, добавить';$('#offer-name').textContent=currentOffer.product.name; $('#offer-amount').textContent=currentOffer.quantity+' × '+money(currentOffer.product.price); $('#offer-error').textContent=''; $('#confirmation').showModal(); } catch(e){message(e.message,'error');} finally {button.disabled=!(Number(p.quantity)>0);} };
 controls.append(label,button);node.append(controls);return node;
}
async function chat(text){ if(busy || !text.trim())return; busy=true; $('#send').disabled=true; message(text,'user'); const pending=message('Проверяю каталог…'); try {const data=await api('/api/chat',{message:text});pending.replaceChildren(el('p','',data.answer)); if(data.notice)pending.append(el('p','warning',data.notice));const list=el('div','products');data.products.forEach(p=>list.append(card(p)));pending.append(list);for(const url of data.sources||[])pending.append(safeLink(url,'Источник: '+new URL(url).pathname+' ↗'));}catch(e){pending.classList.add('error');pending.replaceChildren(el('p','',e.message));}finally{busy=false;$('#send').disabled=false;$('#messages').scrollTop=$('#messages').scrollHeight;} }
$('#composer').addEventListener('submit',e=>{e.preventDefault();const text=$('#question').value;$('#question').value='';chat(text);});
$('#question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('#composer').requestSubmit();}});
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>chat(b.dataset.query));
$('#cancel-offer').onclick=()=>{$('#confirmation').close();currentOffer=null;};
$('#accept-offer').onclick=async()=>{if(!currentOffer)return;$('#accept-offer').disabled=true;try{await api('/api/confirm',{token:currentOffer.token,confirmed:true});$('#confirmation').close();currentOffer=null;if(location.pathname==='/cart'){await cart();return;}const m=message('Товар добавлен в демонстрационную корзину. Это не заказ в ekt.kz.');const a=el('a','','Открыть актуальную корзину →');a.href='/cart';m.append(a);await cart();}catch(e){$('#offer-error').textContent=e.message;}finally{$('#accept-offer').disabled=false;}};
async function cart(){
 const data=await api('/api/cart');$('#cart-count').textContent=data.items.length;
 const box=$('#cart-items');box.replaceChildren();
 const error=el('p','warning');error.hidden=true;error.setAttribute('role','alert');box.append(error);
 if(!data.items.length)box.append(el('p','','Корзина пока пуста.'));
 for(const item of data.items){
  const p=item.product,r=el('div','cart-row');
  r.append(el('strong','',p.name),el('div','',item.quantity+' × '+money(p.price)+' = '+money(item.subtotal)),el('small','','Цена и остаток проверены при последнем изменении. Товар не зарезервирован.'));
  for(const warning of p.warnings||[])r.append(el('p','warning',warning));
  const controls=el('div','cart-controls'),input=el('input');input.type='number';input.min='1';input.step='any';input.value=item.quantity;input.setAttribute('aria-label','Новое количество для '+p.article);
  const update=el('button','','Изменить количество'),remove=el('button','secondary','Удалить');
  update.onclick=async()=>{update.disabled=true;error.hidden=true;try{
   currentOffer=await api('/api/propose',{id:p.id,quantity:Number(input.value),mode:'set'});
   $('#confirmation h2').textContent='Изменить количество?';$('#accept-offer').textContent='Да, изменить';
   $('#offer-name').textContent=currentOffer.product.name;
   $('#offer-amount').textContent='Было: '+currentOffer.previous_quantity+'. Станет: '+currentOffer.quantity+' × '+money(currentOffer.product.price);
   $('#offer-error').textContent='';$('#confirmation').showModal();
  }catch(e){error.textContent=e.message;error.hidden=false;}finally{update.disabled=false;}};
  remove.onclick=async()=>{if(!window.confirm('Удалить из корзины: '+p.name+'?'))return;remove.disabled=true;try{await api('/api/cart/remove',{id:p.id,confirmed:true});await cart();}catch(e){error.textContent=e.message;error.hidden=false;remove.disabled=false;}};
  controls.append(input,update,remove);r.append(controls);box.append(r);
 }
 if(data.items.length)box.append(el('h3','','Итого по сохранённым ценам: '+(data.total===null?'есть позиции без подтверждённой цены':money(data.total))),el('p','muted','Доставка не включена. Это собственная корзина прототипа, заказ в EKT не оформляется.'));
}

async function init(){try{const s=await api('/api/status');csrf=s.csrf;if(s.data_mode==='snapshot'){$('.source strong').textContent='Демо-снимок EKT';$('footer').textContent='Снимок от 23.09.2026: цены и остатки не актуальные. Проверка без ИИ и внешних запросов.';$('.prototype').textContent='Демонстрационные данные • не актуальные цены и остатки. Корзина не создаёт заказ EKT.';$('#upload').disabled=true;}$('#ai-status').textContent=s.ai?'ИИ подключён • ответы по данным каталога':s.data_mode==='snapshot'?'Демо без ИИ • цены и остатки из снимка':'Режим каталога • API-ключ ИИ ещё не подключён';$('#catalog-status').textContent=s.ready?s.count+' товаров в выборке':s.error||'Каталог загружается…';await cart();if(!s.ready&&!s.error)setTimeout(init,2000);}catch(e){$('#catalog-status').textContent=e.message;}}
if(location.pathname==='/cart'){$('#messages').hidden=true;$('#composer').hidden=true;$('#cart-panel').hidden=false;}
init();

$('#upload').onclick=async()=>{
 if(busy)return;
 const file=$('#specification').files[0];
 if(!file){message('Выберите файл спецификации.','error');return;}
 if(!$('#upload-consent').checked){message('Для распознавания нужно согласие на передачу выбранного файла в OpenAI.','error');return;}
 if(file.size>2*1024*1024){message('Файл должен быть не больше 2 МБ.','error');return;}
 busy=true;$('#upload').disabled=true;$('#send').disabled=true;
 const pending=message('Распознаю '+file.name+'… Это может занять до минуты.');
 try{
  const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
  const result=await api('/api/upload',{filename:file.name,data:encoded,consent:true});
  pending.replaceChildren(el('p','','Проверьте распознанные позиции. Нажмите «Найти», чтобы проверить товар в каталоге. Корзина не изменилась.'));
  if(result.note)pending.append(el('p','warning',result.note));
  if(!result.items.length)pending.append(el('p','','Товарные позиции не распознаны. Попробуйте более чёткий файл.'));
  for(const item of result.items){const row=el('div','extracted-row'),query=el('input');query.value=item.query;query.setAttribute('aria-label','Уточнить название или артикул');const button=el('button','','Найти');button.onclick=()=>chat(query.value);row.append(query,el('span','','Количество из файла: '+item.quantity),button);pending.append(row);}
  $('#specification').value='';$('#upload-consent').checked=false;
 }catch(e){pending.replaceChildren(el('p','warning',e.message||'Ошибка чтения файла.'));}
 finally{busy=false;$('#upload').disabled=false;$('#send').disabled=false;}
};
$('#specification').onchange=()=>{$('#upload-consent').checked=false;};

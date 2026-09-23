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
 const button=el('button','','Подготовить добавление'); button.disabled=!(Number(p.quantity)>0); button.onclick=async()=>{ button.disabled=true; try { currentOffer=await api('/api/propose',{id:p.id,quantity:Number(input.value)}); $('#offer-name').textContent=currentOffer.product.name; $('#offer-amount').textContent=currentOffer.quantity+' × '+money(currentOffer.product.price); $('#offer-error').textContent=''; $('#confirmation').showModal(); } catch(e){message(e.message,'error');} finally {button.disabled=!(Number(p.quantity)>0);} };
 controls.append(label,button);node.append(controls);return node;
}
async function chat(text){ if(busy || !text.trim())return; busy=true; $('#send').disabled=true; message(text,'user'); const pending=message('Проверяю каталог…'); try {const data=await api('/api/chat',{message:text});pending.replaceChildren(el('p','',data.answer)); if(data.notice)pending.append(el('p','warning',data.notice));const list=el('div','products');data.products.forEach(p=>list.append(card(p)));pending.append(list);}catch(e){pending.classList.add('error');pending.replaceChildren(el('p','',e.message));}finally{busy=false;$('#send').disabled=false;$('#messages').scrollTop=$('#messages').scrollHeight;} }
$('#composer').addEventListener('submit',e=>{e.preventDefault();const text=$('#question').value;$('#question').value='';chat(text);});
$('#question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('#composer').requestSubmit();}});
document.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>chat(b.dataset.query));
$('#cancel-offer').onclick=()=>{$('#confirmation').close();currentOffer=null;};
$('#accept-offer').onclick=async()=>{if(!currentOffer)return;$('#accept-offer').disabled=true;try{await api('/api/confirm',{token:currentOffer.token,confirmed:true});$('#confirmation').close();currentOffer=null;const m=message('Товар добавлен в демонстрационную корзину. Это не заказ в ekt.kz.');const a=el('a','','Открыть актуальную корзину →');a.href='/cart';m.append(a);await cart();}catch(e){$('#offer-error').textContent=e.message;}finally{$('#accept-offer').disabled=false;}};
async function cart(){const data=await api('/api/cart');$('#cart-count').textContent=data.items.length;const box=$('#cart-items');box.replaceChildren();if(!data.items.length)box.append(el('p','','Корзина пока пуста.'));for(const item of data.items){const r=el('div','cart-row');r.append(el('strong','',item.product.name),el('div','',item.quantity+' × '+money(item.product.price)),el('small','','Цена и остаток проверены при добавлении. Товар не зарезервирован.'));box.append(r);}}
async function init(){try{const s=await api('/api/status');csrf=s.csrf;$('#ai-status').textContent=s.ai?'ИИ подключён • ответы по данным каталога':'Режим каталога • API-ключ ИИ ещё не подключён';$('#catalog-status').textContent=s.ready?s.count+' товаров в выборке':s.error||'Каталог загружается…';await cart();if(!s.ready&&!s.error)setTimeout(init,2000);}catch(e){$('#catalog-status').textContent=e.message;}}
if(location.pathname==='/cart'){$('#messages').hidden=true;$('#composer').hidden=true;$('#cart-panel').hidden=false;}
init();

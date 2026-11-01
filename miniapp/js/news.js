function renderAssets(){document.getElementById('assets-grid').innerHTML=ASSETS.map(function(a){return'<button type="button" onclick="openAsset(\''+a.key+'\')" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left"><span class="text-lg w-7 text-center">'+a.emoji+'</span><div class="flex-1"><div class="text-sm font-medium">'+esc(a.name)+'</div><div class="text-[10px] text-[#848e9c]">'+esc(a.full)+(a.binance?' · Live Binance':a.fx?' · FX spot':' · check availability')+'</div></div><div class="text-xs text-[#848e9c]">'+esc(a.exchange)+'</div></button>';}).join('');}
function renderChips(){document.getElementById('subscribe-chips').innerHTML=ASSETS.map(function(a){return'<button type="button" onclick="toggleSub(\''+a.key+'\')" class="px-2 py-1 rounded text-xs '+(subscribed[a.key]?'bg-[#f0b90b]/15 text-[#f0b90b] border border-[#f0b90b]/40':'bg-[#12161c] text-[#848e9c]')+'">'+esc(a.name)+'</button>';}).join('');}
function switchTab(tab){['home','news','settings'].forEach(function(t){var v=document.getElementById('view-'+t);if(v)v.classList.toggle('hidden',t!==tab);var b=document.getElementById('tab-'+t);if(b)b.className=(t===tab?'tab-on':'text-[#848e9c]')+' flex-1 py-2 rounded-md text-xs';});if(tab==='news'){refreshNews();if(newsTimer)clearInterval(newsTimer);newsTimer=setInterval(refreshNews,60000);}else if(newsTimer){clearInterval(newsTimer);newsTimer=null;}if(tab==='settings'){loadSettingsFromApi();}}
function setSettingsStatus(msg,ok){var el=document.getElementById('settings-sync-status');if(el){el.textContent=msg||'';el.className='text-[10px] mt-3 '+(ok?'text-[#0ecb81]':'text-[#f6465d]');}}
async function loadSettingsFromApi(){if(!window.MacroAPI||!MacroAPI.available()){setSettingsStatus('API не настроен — настройки локально на устройстве.',false);return;}try{var s=await MacroAPI.getSettings();if(s.subscribed_assets){Object.keys(s.subscribed_assets).forEach(function(k){subscribed[k]=!!s.subscribed_assets[k];});renderChips();}notifOn=s.notifications_enabled!==false;document.getElementById('btn-notif').textContent=notifOn?'🔔':'🔇';var b2=document.getElementById('btn-notif2');if(b2){b2.textContent=notifOn?'ON':'OFF';b2.className='text-xs '+(notifOn?'text-[#0ecb81]':'text-[#f6465d]');}setSettingsStatus('Синхронизировано с сервером',true);}catch(e){setSettingsStatus('Ошибка API: '+(e.message||e.code||'error'),false);}}
async function toggleNotif(){notifOn=!notifOn;document.getElementById('btn-notif').textContent=notifOn?'🔔':'🔇';var b2=document.getElementById('btn-notif2');if(b2){b2.textContent=notifOn?'ON':'OFF';b2.className='text-xs '+(notifOn?'text-[#0ecb81]':'text-[#f6465d]');}try{localStorage.setItem('macro_notif',notifOn?'1':'0');}catch(e){}if(window.MacroAPI&&MacroAPI.available()){try{await MacroAPI.patchSettings({notifications_enabled:notifOn});setSettingsStatus('Уведомления сохранены',true);}catch(e){setSettingsStatus('Локально OK, сервер недоступен',false);}}}
async function toggleSub(k){subscribed[k]=!subscribed[k];renderChips();try{localStorage.setItem('macro_subs',JSON.stringify(subscribed));}catch(e){}if(window.MacroAPI&&MacroAPI.available()){try{await MacroAPI.patchSettings({subscribed_assets:subscribed});setSettingsStatus('Подписки сохранены',true);}catch(e){setSettingsStatus('Локально OK, сервер недоступен',false);}}}
function setCat(cat,btn){activeCat=cat;document.querySelectorAll('.cat-btn').forEach(function(b){b.classList.remove('on');});if(btn)btn.classList.add('on');if(newsMode==='ai')renderAINews();}
function setNewsMode(mode){newsMode=mode;document.getElementById('nm-ai').className=(mode==='ai'?'tab-on':'text-[#848e9c]')+' flex-1 py-2 rounded-md text-xs';document.getElementById('nm-calendar').className=(mode==='calendar'?'tab-on':'text-[#848e9c]')+' flex-1 py-2 rounded-md text-xs';document.getElementById('news-title').textContent=mode==='calendar'?'Economic Calendar':'Market News';document.getElementById('news-filters').className=mode==='calendar'?'flex gap-1 mb-2':'hidden';document.getElementById('ff-header').className=mode==='calendar'?'ff-row text-[9px] text-[#848e9c] uppercase tracking-wide bg-[#0f1218]':'hidden';refreshNews();}
async function refreshNews(){if(newsMode==='calendar')await loadCalendar();else await loadAINews();}
function showNewsUnavailable(reason){var list=document.getElementById('news-list');list.innerHTML='<p class="text-center text-[#f6465d] py-8">Новости недоступны</p><p class="text-center text-[#848e9c] text-xs px-4">'+esc(reason||'Источники не ответили')+'</p><div class="text-center mt-3"><button type="button" onclick="loadAINews()" class="text-xs px-3 py-2 border border-[#1e2329] rounded text-[#f0b90b]">↻ Retry</button></div>';document.getElementById('news-updated').textContent='unavailable';allNews=[];}

async function fetchRssJson(rssUrl){
  var proxies=[
    'https://api.rss2json.com/v1/api.json?rss_url='+encodeURIComponent(rssUrl),
    'https://api.allorigins.win/raw?url='+encodeURIComponent(rssUrl)
  ];
  for(var p=0;p<proxies.length;p++){
    try{
      var r=await fetch(proxies[p]+(proxies[p].indexOf('?')>=0?'&':'?')+'_='+Date.now(),{cache:'no-store'});
      if(!r.ok)continue;
      var text=await r.text();
      var j;try{j=JSON.parse(text);}catch(e){j=null;}
      if(j&&j.status==='ok'&&j.items)return j.items;
      if(j&&j.items)return j.items;
      if(text&&text.indexOf('<item')>=0){
        var items=[],re=/<item[\s\S]*?<\/item>/gi,m;
        while((m=re.exec(text))&&items.length<15){
          var block=m[0];
          var title=(block.match(/<title><!\[CDATA\[([\s\S]*?)\]\]><\/title>/)||block.match(/<title>([\s\S]*?)<\/title>/)||[])[1]||'';
          var link=(block.match(/<link>([\s\S]*?)<\/link>/)||[])[1]||'';
          var desc=(block.match(/<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/)||block.match(/<description>([\s\S]*?)<\/description>/)||[])[1]||'';
          var pub=(block.match(/<pubDate>([\s\S]*?)<\/pubDate>/)||[])[1]||'';
          title=title.replace(/<[^>]+>/g,'').trim();
          if(title)items.push({title:title,link:link.trim(),description:desc,pubDate:pub,author:'RSS'});
        }
        if(items.length)return items;
      }
    }catch(e){}
  }
  return[];
}

async function loadAINewsFromRss(){
  var feeds=[
    'https://feeds.bbci.co.uk/news/business/rss.xml',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'https://news.google.com/rss/search?q=forex+OR+bitcoin+OR+gold+OR+%22federal+reserve%22&hl=en-US&gl=US&ceid=US:en',
    'https://www.investing.com/rss/news.rss'
  ];
  var items=[];
  for(var i=0;i<feeds.length;i++){
    var part=await fetchRssJson(feeds[i]);
    if(part&&part.length)items=items.concat(part);
  }
  if(!items.length)return false;
  var seen={};
  allNews=items.filter(function(it){var t=(it.title||'').trim();if(!t||seen[t])return false;seen[t]=1;return true;}).map(function(it){
    var img=safeHttps((it.enclosure&&it.enclosure.link)||it.thumbnail||'');
    var cl=classifyText(it.title,it.description||'');
    return{
      id:it.guid||it.link||it.title,
      title:it.title||'',
      link:safeHttps(it.link||''),
      date:it.pubDate||'',
      source:String(it.author||it.source||'News').slice(0,40),
      desc:String(it.description||'').replace(/<[^>]+>/g,'').slice(0,300),
      image:img,
      cat:cl.cat,
      bias:cl.bias,
      method:'rss',
      analysis_ru:'',
      assets:[],
      confidence:'LOW'
    };
  });
  allNews.sort(function(a,b){return new Date(b.date||0)-new Date(a.date||0);});
  document.getElementById('news-updated').textContent=allNews.length+' news · RSS · '+fmtDT(new Date().toISOString());
  renderAINews();
  return true;
}

async function loadAINews(){
  var list=document.getElementById('news-list');
  list.innerHTML='<p class="text-center text-[#848e9c] py-6">Loading…</p>';
  /* 1) Prefer backend API if configured */
  if(window.MacroAPI&&MacroAPI.available()){
    try{
      var params={limit:30};
      if(activeCat&&activeCat!=='all')params.category=activeCat;
      var data=await MacroAPI.getNews(params);
      var items=(data&&data.items)||[];
      if(items.length){
        allNews=items.map(function(it){return{id:it.id,title:it.title||'',link:safeHttps(it.link||''),date:it.published_at||'',source:String(it.source||'News').slice(0,40),desc:String(it.summary||'').slice(0,300),image:safeHttps(it.image||''),cat:it.category||'economic',bias:it.bias||'NEUTRAL',importance:it.importance||'',confidence:it.confidence||'',analysis_ru:it.analysis_ru||'',method:it.method||'rule-based',assets:it.assets||[]};});
        document.getElementById('news-updated').textContent=allNews.length+' news · API · '+fmtDT(new Date().toISOString());
        renderAINews();
        return;
      }
      /* empty API cache — fall through to RSS */
    }catch(e){
      /* API failed — fall through to RSS */
    }
  }
  /* 2) Public RSS (works without backend) */
  try{
    var ok=await loadAINewsFromRss();
    if(!ok)showNewsUnavailable('RSS-источники не ответили. Нажмите ↻ позже.');
  }catch(e){
    showNewsUnavailable((e&&e.message)||'Ошибка загрузки');
  }
}

function renderAINews(){var list=document.getElementById('news-list');var items=activeCat==='all'?allNews:allNews.filter(function(e){return e.cat===activeCat;});if(!items.length){list.innerHTML='<p class="text-center text-[#848e9c] py-8">Нет новостей в этой категории</p>';return;}window._newsView=items;list.innerHTML='<div class="space-y-2 p-2">'+items.map(function(e,idx){var c=CATS[e.cat]||CATS.economic;var biasCls=e.bias==='BULLISH'?'bias-b':e.bias==='BEARISH'?'bias-r':'bias-n';var biasIcon=e.bias==='BULLISH'?'🟢':e.bias==='BEARISH'?'🔴':'⚪';var img=e.image?'<img class="news-img" src="'+esc(e.image)+'" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'"/>':'';return'<div class="card overflow-hidden news-card" role="button" tabindex="0" onclick="openNewsDetail('+idx+')">'+img+'<div class="p-3"><div class="flex items-center gap-2 text-[10px] mb-1.5 flex-wrap"><span class="text-[#f0b90b]">'+c.emoji+' '+esc(c.name)+'</span><span class="'+biasCls+'">'+biasIcon+' '+esc(e.bias)+'</span><span class="ml-auto text-[#848e9c] font-mono">'+esc(fmtDT(e.date))+'</span></div><div class="text-sm font-semibold mb-1">'+esc(e.title)+'</div>'+(e.desc?'<div class="text-[12px] text-[#848e9c] mb-1">'+esc(e.desc.slice(0,120))+'…</div>':'')+'<div class="text-[10px] text-[#848e9c]">'+esc(timeAgo(e.date))+' · '+esc(e.source)+' · '+esc(e.method||'')+'</div></div></div>';}).join('')+'</div>';}
function openNewsDetail(idx){var items=window._newsView||allNews;var e=items[idx];if(!e)return;var c=CATS[e.cat]||CATS.economic;var biasIcon=e.bias==='BULLISH'?'🟢':e.bias==='BEARISH'?'🔴':'⚪';var biasCls=e.bias==='BULLISH'?'bias-b':e.bias==='BEARISH'?'bias-r':'bias-n';var analysis=e.analysis_ru||('Метод: '+(e.method||'rule-based')+'. Оценка: '+e.bias+'. Не торговая рекомендация.');var assetsHint=(e.assets&&e.assets.length)?e.assets.join(', '):'—';var img=e.image?'<img class="detail-img rounded-lg mb-3" src="'+esc(e.image)+'" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'"/>':'';var linkBtn=e.link?'<button type="button" data-url="'+esc(e.link)+'" onclick="openSafeLink(this.getAttribute(\''+'data-url'+'\'))" class="w-full py-3 rounded-lg border border-[#1e2329] text-sm text-[#848e9c] mb-2">🌐 Открыть первоисточник</button>':'';var html=img+'<div class="flex flex-wrap gap-2 mb-3 text-[11px]"><span class="px-2 py-1 rounded bg-[#1e2329] text-[#f0b90b]">'+c.emoji+' '+esc(c.name)+'</span><span class="px-2 py-1 rounded bg-[#1e2329] '+biasCls+'">'+biasIcon+' '+esc(e.bias)+'</span><span class="px-2 py-1 rounded bg-[#1e2329] text-[#848e9c]">'+esc(e.source)+'</span><span class="px-2 py-1 rounded bg-[#1e2329] text-[#848e9c]">'+esc(e.method||'')+'</span></div><h1 class="text-lg font-semibold leading-snug mb-2">'+esc(e.title)+'</h1><div class="text-[11px] text-[#848e9c] font-mono mb-4">'+esc(fmtDT(e.date))+' · '+esc(timeAgo(e.date))+'</div><div class="card p-3 mb-3"><div class="text-[10px] text-[#848e9c] uppercase mb-1">Что произошло</div><div class="text-sm leading-relaxed">'+esc(e.desc||e.title)+'</div></div><div class="card p-3 mb-3"><div class="text-[10px] text-[#848e9c] uppercase mb-1">Активы</div><div class="text-sm text-[#f0b90b]">'+esc(assetsHint)+'</div></div><div class="card p-3 mb-3"><div class="text-[10px] text-[#848e9c] uppercase mb-1">Анализ</div><div class="text-sm leading-relaxed">'+esc(analysis)+'</div><div class="text-[10px] text-[#848e9c] mt-2">Confidence: '+esc(e.confidence||'LOW')+' · Не финансовый совет</div></div>'+linkBtn+'<button type="button" onclick="closeNewsDetail()" class="w-full py-3 rounded-lg bg-[#1e2329] text-sm text-[#f0b90b] font-medium">← Назад к ленте</button>';document.getElementById('news-detail-body').innerHTML=html;document.getElementById('app-main').classList.add('hidden');document.getElementById('app-news-detail').classList.remove('hidden');document.getElementById('app-news-detail').scrollTop=0;if(tg){try{tg.BackButton.show();tg.BackButton.onClick(closeNewsDetail);}catch(err){}}}
function closeNewsDetail(){document.getElementById('app-news-detail').classList.add('hidden');document.getElementById('app-main').classList.remove('hidden');if(tg){try{tg.BackButton.hide();}catch(e){}}}
function normalizeCalEvent(e){return{title:e.name||e.title||'',currency:e.currency||e.country||'',impact:e.impact||'Low',date:e.date||'',forecast:e.forecast||e.estimate||'',previous:e.previous||'',actual:e.actual||'',provider:e.provider||e._provider||''};}

async function loadCalendarDirect(){
  var data=[],src='';
  try{
    var r=await fetch('https://nfs.faireconomy.media/ff_calendar_thisweek.json?t='+Date.now(),{cache:'no-store'});
    if(r.ok){
      var j=await r.json();
      if(Array.isArray(j)&&j.length){
        data=j.map(function(e){e.provider='faireconomy (FF calendar feed)';return e;});
        src='faireconomy';
      }
    }
  }catch(e){}
  if(!data.length){
    try{
      var r2=await fetch('https://pipatlas.com/api/calendar?t='+Date.now(),{cache:'no-store'});
      if(r2.ok){
        var j2=await r2.json();
        var ev=j2.events||j2||[];
        if(Array.isArray(ev)&&ev.length){data=ev.map(function(e){e.provider='pipatlas';return e;});src='pipatlas';}
      }
    }catch(e){}
  }
  if(!data.length)return false;
  calEvents=data.map(normalizeCalEvent);
  var seen={};
  calEvents=calEvents.filter(function(e){var k=(e.title+'|'+e.date);if(seen[k])return false;seen[k]=1;return !!e.title;});
  document.getElementById('news-updated').textContent=calEvents.length+' events · '+src+' · updated '+fmtDT(new Date().toISOString());
  renderCalendar();
  return true;
}

async function loadCalendar(){
  var list=document.getElementById('news-list');
  list.innerHTML='<p class="text-center text-[#848e9c] py-6">Loading calendar…</p>';
  if(window.MacroAPI&&MacroAPI.available()){
    try{
      var data=await MacroAPI.getCalendar();
      var items=(data&&data.items)||[];
      if(items.length){
        calEvents=items.map(normalizeCalEvent);
        document.getElementById('news-updated').textContent=calEvents.length+' events · API · updated '+fmtDT(new Date().toISOString());
        renderCalendar();
        return;
      }
    }catch(e){}
  }
  try{
    var ok=await loadCalendarDirect();
    if(!ok){
      list.innerHTML='<p class="text-center text-[#f6465d] py-8">Календарь недоступен</p><p class="text-center text-[#848e9c] text-xs">Нажмите ↻ позже</p>';
      document.getElementById('news-updated').textContent='unavailable';
    }
  }catch(e){
    list.innerHTML='<p class="text-center text-[#f6465d] py-8">Календарь недоступен</p>';
    document.getElementById('news-updated').textContent='unavailable';
  }
}

function renderCalendar(){var list=document.getElementById('news-list');var items=newsFilter==='all'?calEvents:calEvents.filter(function(e){var i=(e.impact||'').toLowerCase();if(newsFilter==='High')return i==='high'||i==='red';if(newsFilter==='Medium')return i==='medium'||i==='orange';if(newsFilter==='Low')return i==='low'||i==='holiday'||i==='';return true;});items=items.slice().sort(function(a,b){return new Date(a.date||0)-new Date(b.date||0);});if(!items.length){list.innerHTML='<p class="text-center text-[#848e9c] py-8">Нет событий</p>';return;}var lastDay='';list.innerHTML=items.map(function(e){var day=fmtDate(e.date);var head=day!==lastDay?'<div class="px-3 py-1.5 text-[10px] text-[#f0b90b] bg-[#0f1218] border-b border-[#1e2329] font-semibold">'+esc(day)+'</div>':'';lastDay=day;return head+'<div class="ff-row text-left"><span class="text-[11px] font-mono">'+esc(fmtTime(e.date))+'</span><span class="text-[11px] font-semibold text-[#f0b90b]">'+esc(e.currency||'')+'</span><span class="imp '+impactClass(e.impact)+'"></span><div><div class="text-[12px]">'+esc(e.title)+'</div><div class="ff-vals"><div><span class="text-[#848e9c]">Act </span>'+esc(e.actual||'—')+'</div><div><span class="text-[#848e9c]">Fcst </span>'+esc(e.forecast||'—')+'</div><div><span class="text-[#848e9c]">Prev </span>'+esc(e.previous||'—')+'</div></div></div></div>';}).join('');}
function filterNews(level,btn){newsFilter=level;document.querySelectorAll('.news-f').forEach(function(b){b.className='news-f px-2 py-1 rounded text-xs text-[#848e9c] bg-[#12161c]';});if(btn)btn.className='news-f tab-on px-2 py-1 rounded text-xs';if(newsMode==='calendar')renderCalendar();}
document.addEventListener('visibilitychange',function(){if(!document.hidden&&typeof refreshNews==='function'){try{refreshNews();}catch(e){}}});
try{renderAssets();renderChips();}catch(e){}

(()=>{
  'use strict';
  const query=(s)=>document.querySelector(s);
  const queryAll=(s)=>Array.from(document.querySelectorAll(s));
  const feedbackDescriptions={
    demonstrations:'Examples of behaviour show the agent what actions or trajectories it should reproduce.',
    preferences:'Comparisons between alternatives reveal which actions or outcomes a person prefers.',
    corrections:'Human interventions indicate how an action or trajectory should be adjusted.',
    proxy:'Evaluative signals guide learning without explicitly specifying the complete underlying objective.'
  };
  const feedbackDescription=query('#feedback-hover-description');
  function showFeedbackDescription(key){if(!feedbackDescription||!feedbackDescriptions[key])return;feedbackDescription.textContent=feedbackDescriptions[key];feedbackDescription.classList.add('is-visible');}
  function hideFeedbackDescription(){if(feedbackDescription)feedbackDescription.classList.remove('is-visible');}
  function toggleFeedback(key){
    const button=query(`.feedback-tab[data-feedback="${key}"]`);if(!button)return;
    const selected=button.getAttribute('aria-pressed')!=='true';
    button.classList.toggle('active',selected);button.setAttribute('aria-pressed',String(selected));
    queryAll(`[data-node="${key}"],[data-path="${key}"]`).forEach(el=>el.classList.toggle('selected',selected));
  }
  queryAll('.feedback-tab').forEach((btn,i,buttons)=>{
    btn.addEventListener('click',()=>toggleFeedback(btn.dataset.feedback));
    btn.addEventListener('keydown',e=>{
      if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;
      e.preventDefault();const increment=e.key==='ArrowRight'?1:-1;
      buttons[(i+increment+buttons.length)%buttons.length].focus();
    });
  });
  queryAll('[data-node]').forEach(node=>{
    node.addEventListener('mouseenter',()=>showFeedbackDescription(node.dataset.node));
    node.addEventListener('mouseleave',hideFeedbackDescription);
    node.addEventListener('focus',()=>showFeedbackDescription(node.dataset.node));
    node.addEventListener('blur',hideFeedbackDescription);
  });
  const toggle=query('#nav-trigger'),mobile=query('#mobile-nav');
  function close(){if(!toggle||!mobile)return;toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-label','Open navigation');mobile.hidden=true;}
  if(toggle&&mobile){
    toggle.addEventListener('click',()=>{const expanded=toggle.getAttribute('aria-expanded')==='true';if(expanded)close();else{mobile.hidden=false;toggle.setAttribute('aria-expanded','true');toggle.setAttribute('aria-label','Close navigation');}});
    queryAll('.mobile-nav a').forEach(a=>a.addEventListener('click',close));
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!mobile.hidden){close();toggle.focus();}});
    window.addEventListener('resize',()=>{if(window.innerWidth>890)close();});
  }
  const header=query('.site-header');
  function updateHeader(){if(header)header.classList.toggle('is-scrolled',window.scrollY>12);}
  if(header){window.addEventListener('scroll',updateHeader,{passive:true});updateHeader();}
  const progress=query('#project-progress'),progressValue=query('#project-progress-value');
  if(progress&&progressValue){
    const start=Date.UTC(2026,0,1),end=Date.UTC(2029,0,1);
    const elapsed=Math.max(0,Math.min(100,Math.round((Date.now()-start)/(end-start)*100)));
    progress.style.setProperty('--project-progress',`${elapsed}%`);
    progress.setAttribute('aria-valuenow',String(elapsed));progressValue.textContent=`${elapsed}%`;
  }
  const year=query('#year');
  if(year)year.textContent=String(new Date().getFullYear());
  if('IntersectionObserver' in window){
    const links=queryAll('.desktop-nav a');const io=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting)for(const a of links){if(a.hash.slice(1)===e.target.id)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');}},{rootMargin:'-20% 0px -72% 0px'});
    for(const a of links){const t=query(a.hash);if(t)io.observe(t);}
  }
})();

// Accessible citation copy controls matching the bibliography source website.
document.addEventListener('click', async (event) => {
  const btn = event.target.closest('button.citation-copy');
  if (!btn) return;
  const citation = btn.dataset.citation;
  if (!citation) return;
  try {
    await navigator.clipboard.writeText(citation);
    const old = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = old; btn.classList.remove('copied'); }, 1800);
  } catch (err) {
    // Clipboard access may be unavailable when opening this site over file://.
    btn.textContent = 'Copy unavailable';
    setTimeout(() => { btn.textContent = 'Copy citation'; }, 1800);
  }
});


// Publication filters and counters. No external APIs, no client-side BibTeX fetching.
(()=>{
  'use strict';
  const publications=[...document.querySelectorAll('#publications .publication')];
  const filters=[...document.querySelectorAll('#publications .publication-filter')];
  const status=document.getElementById('publication-filter-status');
  const total=document.getElementById('publication-total-count');
  if(total) total.textContent=`${publications.length} publications`;
  const categoryNames={all:'publications',conferences:'conference papers',journals:'journal articles',workshops:'workshop papers'};
  for(const btn of filters){
    const key=btn.dataset.filter;
    const count=key==='all'?publications.length:publications.filter(p=>p.dataset.category===key).length;
    const badge=btn.querySelector('.publication-filter-count');
    if(badge)badge.textContent=String(count);
    btn.addEventListener('click',()=>{
      let shown=0;
      for(const pub of publications){
        pub.hidden=key!=='all' && pub.dataset.category!==key;
        if(!pub.hidden)shown++;
      }
      for(const other of filters){
        const active=other===btn;
        other.classList.toggle('is-active',active);
        other.setAttribute('aria-pressed',String(active));
      }
      if(status)status.textContent=`Showing ${shown} ${categoryNames[key]||'publications'}.`;
    });
  }
  for(const [selector,id,singular,plural] of [
    ['repository','repository-count','repository','repositories'],
    ['dataset','dataset-count','dataset','datasets']
  ]){
    const output=document.getElementById(id);
    if(!output)continue;
    const count=document.querySelectorAll(`#software .resource-sublist li[data-resource="${selector}"] a[href]`).length;
    output.textContent=`${count} ${count===1?singular:plural}`;
  }
})();

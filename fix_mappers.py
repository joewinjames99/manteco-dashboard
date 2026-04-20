import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manteco_dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 1163-1219 (0-indexed 1162-1218) — the comment block + 4 mapper functions
# Line 1163 = comment block start, line 1219 = closing } of mapResale + blank line
# We'll replace 1163-1219 (1-indexed) = indices 1162-1219 (exclusive)

new_block = r"""// Column normalization: lowercase + spaces→_ + remove non-[a-z0-9_]
// "Type (M/C)"         → type_mc           "Product Name"     → product_name
// "Retail Price ($)"   → retail_price_      "Sale Price ($)"   → sale_price_
// "Markdown %"         → markdown_          "Resale Price ($)" → resale_price_
// "Residual %"         → residual_          "Product URL"      → product_url
// "Manteco Prod. ID"   → manteco_prod_id    "Control Prod. ID" → control_prod_id
// "M: Retail ($)"      → m_retail_          "C: Retail ($)"    → c_retail_
// "Premium $"          → premium_ (1st)     "Premium %"        → premium_1 (2nd, dedup)
// "M: Sale ($)"        → m_sale_            "C: Sale ($)"      → c_sale_
// "M: MD%"             → m_md               "C: MD%"           → c_md
// "Delta (pp)"         → delta_pp           "Side (M/C)"       → side_mc
// "Original Retail ($)"→ original_retail_   "Listing Date"     → listing_date
//
// Sheet stores percentages as decimals (0.769 = 76.9%). normPct normalises.
function normPct(v){ if(v===null)return null; return (Math.abs(v)<=5)?v*100:v; }

function mapProducts(rows){
  return rows.map(function(r){return{
    id:str(r.id),
    type:str(r.type_mc||r.type),
    brand:str(r.brand),
    name:str(r.product_name||r.name),
    category:str(r.category),season:str(r.season),
    retailPrice:num(r.retail_price_||r.retail_price||r.retail),
    salePrice:num(r.sale_price_||r.sale_price||r.sale),
    markdownPct:normPct(num(r.markdown_||r.markdown_pct)),
    resalePrice:num(r.resale_price_||r.resale_price),
    residualPct:normPct(num(r.residual_||r.residual_pct)),
    fabric:str(r.fabric),url:str(r.product_url||r.url)||'#',
  };}).filter(function(r){return r.id&&r.brand;});
}
function mapPairs(rows){
  return rows.map(function(r){return{
    pairId:str(r.pair_id),brand:str(r.brand),tier:str(r.tier),
    category:str(r.category),season:str(r.season),
    mantecoId:str(r.manteco_prod_id||r.manteco_product_id||r.manteco_id),
    controlId:str(r.control_prod_id||r.control_product_id||r.control_id),
    mRetail:num(r.m_retail_||r.m_retail),
    cRetail:num(r.c_retail_||r.c_retail),
    premiumDollar:num(r.premium_||r.premium_dollar||r.premium_usd),
    premiumPct:normPct(num(r.premium_1||r.premium_pct)),
  };}).filter(function(r){return r.pairId&&r.mantecoId;});
}
function mapMarkdown(rows){
  return rows.map(function(r){return{
    pairId:str(r.pair_id),brand:str(r.brand),
    mRetail:num(r.m_retail_||r.m_retail),
    mSale:num(r.m_sale_||r.m_sale),
    mMdPct:normPct(num(r.m_md||r.m_md_pct)),
    cRetail:num(r.c_retail_||r.c_retail),
    cSale:num(r.c_sale_||r.c_sale),
    cMdPct:normPct(num(r.c_md||r.c_md_pct)),
    deltaPp:normPct(num(r.delta_pp)),
    mSaleUrl:str(r.m_sale_url)||'#',cSaleUrl:str(r.c_sale_url)||'#',
  };}).filter(function(r){return r.pairId;});
}
function mapResale(rows){
  return rows.map(function(r){return{
    pairId:str(r.pair_id),
    side:str(r.side_mc||r.side),
    platform:str(r.platform),
    originalRetail:num(r.original_retail_||r.original_retail||r.retail),
    resalePrice:num(r.resale_price_||r.resale_price),
    residualPct:normPct(num(r.residual_||r.residual_pct)),
    age:str(r.age||r.age_yrs),condition:str(r.condition),
    date:str(r.listing_date||r.date),
    listingUrl:str(r.listing_url||r.url)||'#',
  };}).filter(function(r){return r.pairId&&r.side;});
}

// ── KPI render: recomputes all dashboard KPIs from the live arrays ─────────
function renderKPIs(){
  if(!PAIRS.length) return;
  var FF=['Zara','Mango','H&M','MANGO'];
  function inFF(b){return FF.indexOf(b)>=0;}
  var ffP=PAIRS.filter(function(p){return inFF(p.brand);});
  var cpP=PAIRS.filter(function(p){return !inFF(p.brand);});
  var avgPrem=avg(PAIRS.map(function(p){return p.premiumPct||0;}));
  var passN=PAIRS.filter(function(p){return p.premiumPct>=10;}).length;
  var passPct=Math.round(passN/PAIRS.length*100);
  var avgM=avg(PAIRS.map(function(p){return p.mRetail||0;}));
  var avgC=avg(PAIRS.map(function(p){return p.cRetail||0;}));
  var ffAvg=ffP.length?avg(ffP.map(function(p){return p.premiumPct||0;})):0;
  var cpAvg=cpP.length?avg(cpP.map(function(p){return p.premiumPct||0;})):0;
  var ffPass=ffP.filter(function(p){return p.premiumPct>=10;}).length;
  var cpPass=cpP.filter(function(p){return p.premiumPct>=10;}).length;
  var ffAvgM=ffP.length?avg(ffP.map(function(p){return p.mRetail||0;})):0;
  var ffAvgC=ffP.length?avg(ffP.map(function(p){return p.cRetail||0;})):0;
  var cpAvgM=cpP.length?avg(cpP.map(function(p){return p.mRetail||0;})):0;
  var cpAvgC=cpP.length?avg(cpP.map(function(p){return p.cRetail||0;})):0;
  var mMdR=MARKDOWN.filter(function(m){return m.mMdPct!==null;});
  var cMdR=MARKDOWN.filter(function(m){return m.cMdPct!==null;});
  var bothMd=MARKDOWN.filter(function(m){return m.mMdPct!==null&&m.cMdPct!==null;});
  var avgMMd=mMdR.length?avg(mMdR.map(function(m){return m.mMdPct;})):null;
  var avgCMd=cMdR.length?avg(cMdR.map(function(m){return m.cMdPct;})):null;
  var avgDelta=bothMd.length?avg(bothMd.map(function(m){return m.deltaPp;})):null;
  var mRes=RESALE.filter(function(r){return r.side==='Manteco'&&r.residualPct!==null;});
  var cRes=RESALE.filter(function(r){return r.side==='Control'&&r.residualPct!==null;});
  var avgMRes=mRes.length?avg(mRes.map(function(r){return r.residualPct;})):null;
  var avgCRes=cRes.length?avg(cRes.map(function(r){return r.residualPct;})):null;
  var pairedR=mRes.filter(function(r){return cRes.find(function(c){return c.pairId===r.pairId;});});
  var resDiff=(avgMRes!==null&&avgCRes!==null)?avgMRes-avgCRes:null;
  function el(id,v){var e=document.getElementById(id);if(e&&v!==undefined&&v!==null)e.textContent=v;}
  function sgn(v,dec,sfx){return v===null?'—':(v>=0?'+':'')+v.toFixed(dec===undefined?1:dec)+(sfx||'%');}
  // Hero
  el('hero-avg-premium',sgn(avgPrem));
  el('hero-pairs-pass',passPct+'%');
  el('hero-verdict-sub',passN+' of '+PAIRS.length+' pairs \u226510%');
  el('hero-resale-residual',avgMRes!==null?avgMRes.toFixed(1)+'%':'—');
  // Overview KPIs
  el('ov-kpi-premium',sgn(avgPrem));
  el('ov-kpi-pairs',passN+' / '+PAIRS.length);
  el('ov-kpi-pairs-sub',passPct+'% of matched pairs');
  el('ov-kpi-md',avgMMd!==null?avgMMd.toFixed(1)+'%':'—');
  el('ov-kpi-md-sub',avgCMd!==null?'vs '+avgCMd.toFixed(1)+'% control ('+bothMd.length+' paired)':'—');
  el('ov-kpi-resale',avgMRes!==null?avgMRes.toFixed(1)+'%':'—');
  el('ov-kpi-resale-sub',mRes.length+' Manteco listings');
  el('ov-kpi-total',PRODUCTS.length);
  el('ov-kpi-total-sub',PRODUCTS.filter(function(p){return p.type==='Manteco';}).length+' Manteco \u00b7 '+PRODUCTS.filter(function(p){return p.type==='Control';}).length+' Control');
  // Lifecycle
  el('lc-s2-metric',sgn(avgPrem));
  el('lc-s2-desc','Average retail premium across '+PAIRS.length+' matched pairs. '+passN+' of '+PAIRS.length+' pairs ('+passPct+'%) meet or exceed the 10% benchmark. Fast Fashion avg: '+sgn(ffAvg)+'.');
  el('lc-s3-metric',avgDelta!==null?sgn(avgDelta,1,'pp'):'—');
  el('lc-s4-metric',avgMRes!==null?avgMRes.toFixed(1)+'%':'—');
  el('lc-s4-desc',mRes.length+' Manteco listings avg '+( avgMRes!==null?avgMRes.toFixed(1)+'%':'—')+(avgCRes!==null?' vs '+avgCRes.toFixed(1)+'% Control ('+resDiff.toFixed(1)+'pp diff)':'')+'. '+pairedR.length+' pairs with both sides.');
  // Tier cards
  el('tier-ff-prem',sgn(ffAvg));
  el('tier-ff-meta',ffP.length+' pairs \u00b7 '+ffPass+'/'+ffP.length+' \u226510% \u00b7 Brands: Zara, Mango, H&M');
  el('tier-ff-m-avg','$'+Math.round(ffAvgM));el('tier-ff-c-avg','$'+Math.round(ffAvgC));
  if(ffAvgM){var b=document.getElementById('tier-ff-c-bar');if(b)b.style.width=Math.min(100,Math.round(ffAvgC/ffAvgM*100))+'%';}
  el('tier-cp-prem',sgn(cpAvg));
  el('tier-cp-meta',cpP.length+' pairs \u00b7 '+cpPass+'/'+cpP.length+' \u226510% \u00b7 Brands: COS, Woolrich, Fortela, Selected, Aritzia, Karen Millen');
  el('tier-cp-m-avg','$'+Math.round(cpAvgM));el('tier-cp-c-avg','$'+Math.round(cpAvgC));
  if(cpAvgM){var b=document.getElementById('tier-cp-c-bar');if(b)b.style.width=Math.min(100,Math.round(cpAvgC/cpAvgM*100))+'%';}
  // Stage 2
  el('s2-kpi-premium',sgn(avgPrem));
  el('s2-kpi-pairs',passN+' / '+PAIRS.length);
  el('s2-kpi-pairs-sub',passPct+'% pass rate');
  el('s2-kpi-m-retail','$'+avgM.toFixed(2));
  el('s2-kpi-c-retail','$'+avgC.toFixed(2));
  // Stage 3
  el('s3-kpi-m-md',avgMMd!==null?avgMMd.toFixed(1)+'%':'—');
  el('s3-kpi-c-md',avgCMd!==null?avgCMd.toFixed(1)+'%':'—');
  el('s3-kpi-delta',avgDelta!==null?sgn(avgDelta,1,'pp'):'—');
  el('s3-kpi-coverage',bothMd.length+' / '+PAIRS.length);
  // Stage 4
  el('s4-kpi-m-res',avgMRes!==null?avgMRes.toFixed(1)+'%':'—');
  el('s4-kpi-m-res-sub',mRes.length+' Manteco listings');
  el('s4-kpi-c-res',avgCRes!==null?avgCRes.toFixed(1)+'%':'—');
  el('s4-kpi-diff',resDiff!==null?sgn(resDiff,1,'pp'):'—');
  el('s4-kpi-paired',pairedR.length);
  // Topbar
  el('topbar-products',PRODUCTS.length);
  el('topbar-pairs',PAIRS.length);
  var tb=document.getElementById('tab-prod-count');if(tb)tb.textContent=PRODUCTS.length;
  el('topbar-premium',(avgPrem>=0?'+':'')+avgPrem.toFixed(1)+'%');
}
"""

new_lines = [l + '\n' for l in new_block.split('\n')]

# Replace lines 1163-1219 (0-indexed 1162..1218 inclusive, i.e. [:1162] + new + [1219:])
# But the comment block starts at line 1163 (0-indexed 1162). Let's find it exactly.
start = None
end = None
for i, l in enumerate(lines):
    if '// â Column name' in l or '// "Sale Price"' in l or '// Column name' in l:
        if start is None: start = i
    if start is not None and '// LIVE SYNC ENGINE' in l:
        end = i
        break

if start is None:
    # fallback: use known line numbers
    start = 1162  # line 1163 (0-indexed)
    end = 1219    # line 1220 (0-indexed), which is '// LIVE SYNC ENGINE' comment separator line...
    # Actually 1219 is the blank line after mapResale closing brace
    # The '// LIVE SYNC ENGINE' is line 1221 (1-indexed) = index 1220
    # So we want to replace lines 1162..1219 (up to but not including 1220)

    # Let's find by content
    for i, l in enumerate(lines):
        if 'mapProducts' in l and start is None:
            # go back a few to get the comment
            start = max(0, i-12)
        if start is not None and '// ═' in l and i > start + 50:
            end = i
            break

print(f'Replacing lines {start+1} to {end} (0-indexed {start}..{end-1})')
result = lines[:start] + new_lines + lines[end:]

with open('manteco_dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f'Done. File now has {len(result)} lines.')

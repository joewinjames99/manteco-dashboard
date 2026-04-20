import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manteco_dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Verify markers
for i, l in enumerate(lines, 1):
    if "id:'M003'" in l or "let PAIRS" in l or "let MARKDOWN" in l or "let RESALE" in l or "// UTILS" in l:
        print(i, repr(l[:60]))

real_data = r"""  // ── Real research data P03-P62 ───────────────────────────────
  {id:'P03',type:'Manteco',brand:'EAVES',name:'Yaron Manteco Wool Coat',category:'Coat',season:'CW26',retailPrice:495,salePrice:421,markdownPct:14.9,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P04',type:'Manteco',brand:'EAVES',name:'x Coco Oak Manteco Wool Blazer Jacket',category:'Jacket',season:'FW25',retailPrice:499,salePrice:160,markdownPct:67.9,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P05',type:'Manteco',brand:'MANGO',name:'Manteco wool coat with fur collar',category:'Coat',season:'CW26',retailPrice:329,salePrice:249.99,markdownPct:24.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P06',type:'Manteco',brand:'MANGO',name:'Manteco wool coat with lapels',category:'Coat',season:'CW26',retailPrice:349.99,salePrice:149.99,markdownPct:57.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P07',type:'Manteco',brand:'Fortela',name:'Bobbie Giacca Classica Doppiopetto In Flanella',category:'Jacket',season:'FW25',retailPrice:800,salePrice:800,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P08',type:'Manteco',brand:'MANGO',name:"Men's Manteco wool coat with lapels",category:'Coat',season:'CW26',retailPrice:399,salePrice:279,markdownPct:30.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P09',type:'Manteco',brand:'Zara',name:'STRAIGHT COAT WITH MANTECO WOOL ZW COLLECTION',category:'Coat',season:'CW26',retailPrice:299,salePrice:299,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P10',type:'Control',brand:'Zara',name:'WOOL BLEND SHORT COAT ZW COLLECTION',category:'Coat',season:'CW26',retailPrice:169,salePrice:169,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P11',type:'Manteco',brand:'Zara',name:'MANTECO ORIGINS WATER REPELLENT TRENCH COAT',category:'Coat',season:'CW26',retailPrice:229,salePrice:229,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P12',type:'Control',brand:'Zara',name:'PARKA TECNICA CON GILET REMOVIBILE',category:'Coat',season:'CW26',retailPrice:139,salePrice:139,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P13',type:'Control',brand:'MANGO',name:'CAPPOTTO LANA SPIGATO',category:'Coat',season:'CW26',retailPrice:199.99,salePrice:99.99,markdownPct:50.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P14',type:'Control',brand:'MANGO',name:'Woollen coat with belt',category:'Coat',season:'CW26',retailPrice:429.99,salePrice:269.99,markdownPct:37.2,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P15',type:'Manteco',brand:'Woolrich',name:'2-in-1 Sideline Parka in Manteco Recycled Wool Blend',category:'Coat',season:'CW26',retailPrice:1320,salePrice:925,markdownPct:29.9,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P16',type:'Control',brand:'Woolrich',name:'Giacca a camicia in misto lana con motivo a quadri',category:'Jacket',season:'CW26',retailPrice:295,salePrice:149,markdownPct:49.5,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P17',type:'Manteco',brand:'KarenMillen',name:'Italian Manteco Wool Blend Wrap Belted Tailored Midi Coat',category:'Coat',season:'CW26',retailPrice:188,salePrice:48,markdownPct:74.5,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P18',type:'Control',brand:'KarenMillen',name:'Wool Tailored Flared Skirt Midi Coat',category:'Coat',season:'CW26',retailPrice:509,salePrice:305,markdownPct:40.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P19',type:'Manteco',brand:'Zara',name:'MANTECO WOOL COAT ZW COLLECTION LIMITED EDITION',category:'Coat',season:'CW26',retailPrice:269,salePrice:269,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P20',type:'Control',brand:'Zara',name:'CAPPOTTO DOPPIOPETTO MISTO LANA CON CINTURA',category:'Coat',season:'CW26',retailPrice:99.95,salePrice:99.95,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P21',type:'Manteco',brand:'Harrods',name:'Wool-Blend Overcoat',category:'Coat',season:'CW26',retailPrice:720,salePrice:720,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P22',type:'Control',brand:'Toteme',name:'double-breasted wool coat',category:'Coat',season:'CW26',retailPrice:1162,salePrice:1162,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P23',type:'Manteco',brand:'Degliuberti',name:'Installation Coat',category:'Coat',season:'CW26',retailPrice:850,salePrice:680,markdownPct:20.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P24',type:'Control',brand:'DE BONNE FACTURE',name:'Camargue Wool Coat',category:'Coat',season:'CW26',retailPrice:995,salePrice:995,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P25',type:'Manteco',brand:'Isto',name:'RECYCLED WOOL WORK JACKET',category:'Coat',season:'CW26',retailPrice:300,salePrice:150,markdownPct:50.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P26',type:'Control',brand:'Frame',name:'Wool Chore Jacket',category:'Coat',season:'CW26',retailPrice:650,salePrice:325,markdownPct:50.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P27',type:'Manteco',brand:'Zero Barra Cento',name:'Soft Short Recycled Wool Trench Coat',category:'Coat',season:'CW26',retailPrice:466.56,salePrice:466.56,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P28',type:'Control',brand:'Officine Generale',name:'Aretha Coat',category:'Coat',season:'CW26',retailPrice:903,salePrice:495,markdownPct:45.2,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P29',type:'Manteco',brand:'Aritzia',name:'Portfolio Double Face Coat',category:'Coat',season:'CW26',retailPrice:378,salePrice:188,markdownPct:50.3,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P30',type:'Control',brand:'Universal Standard',name:'Double Face Luxe Coat',category:'Coat',season:'CW26',retailPrice:388,salePrice:155,markdownPct:60.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P31',type:'Manteco',brand:'Cyrillus',name:'MANTEAU CABAN LAINAGE UNI FEMME',category:'Coat',season:'CW26',retailPrice:300,salePrice:300,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P32',type:'Control',brand:'Vestiere Collective',name:'Massimo Dutti-Capotto in lana',category:'Coat',season:'FW25',retailPrice:434,salePrice:434,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P33',type:'Manteco',brand:'COS',name:'WOOL-BLEND LONG TRENCH COAT',category:'Trench',season:'FW25',retailPrice:299,salePrice:299,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P34',type:'Manteco',brand:'COS',name:'OVERSIZED DOUBLE-BREASTED WOOL LONG COAT',category:'Coat',season:'CW26',retailPrice:449,salePrice:449,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P35',type:'Manteco',brand:'Fortela',name:'Fortela Winston Double-Breasted Checked Wool Coat',category:'Coat',season:'CW26',retailPrice:1740,salePrice:1740,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P36',type:'Control',brand:'Dries Van Noten',name:'Black Wool Coat',category:'Coat',season:'CW26',retailPrice:2235,salePrice:782,markdownPct:65.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P37',type:'Control',brand:'NN07',name:'Alban 8447 Wool-Blend Felt Jacket',category:'Jacket',season:'CW26',retailPrice:530,salePrice:530,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P38',type:'Control',brand:'Closed',name:'Classic wool-blend coat',category:'Coat',season:'CW26',retailPrice:650,salePrice:325,markdownPct:50.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P39',type:'Control',brand:'Bellerose',name:'DATAIR ANGORA-BLEND CARDIGAN',category:'Knitwear',season:'CW26',retailPrice:179,salePrice:179,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P40',type:'Control',brand:'Arket',name:'WOOL-ALPACA BLEND COAT',category:'Coat',season:'CW26',retailPrice:379,salePrice:379,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P41',type:'Manteco',brand:'H&M',name:'CAPPOTTO A DOPPIO PETTO IN LANA',category:'Coat',season:'CW26',retailPrice:249,salePrice:119,markdownPct:52.2,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P42',type:'Manteco',brand:'H&M',name:'CAPPOTTO LUNGO SARTORIALE DOPPIOPETTO IN LANA',category:'Coat',season:'CW26',retailPrice:279,salePrice:195,markdownPct:30.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P43',type:'Manteco',brand:'H&M',name:'CAPPOTTO A DOPPIO PETTO IN TWEED DI MISTO LANA',category:'Coat',season:'CW26',retailPrice:149,salePrice:119,markdownPct:20.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P44',type:'Manteco',brand:'SELECTED',name:'MISCELA DI LANA',category:'Coat',season:'CW26',retailPrice:279,salePrice:279,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P45',type:'Manteco',brand:'Mango',name:'CAPPOTTO LANA MANTECO COLLO PELLICCIA',category:'Coat',season:'CW26',retailPrice:199,salePrice:149,markdownPct:25.1,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P46',type:'Manteco',brand:'Zara',name:'GIUBBOTTO MISTO LANA MANTECO ORIGINS',category:'Coat',season:'CW26',retailPrice:179,salePrice:179,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P47',type:'Manteco',brand:'Zara',name:'CAPPOTTO MISTO LANA MANTECO ZW COLLECTION LIMITED EDITION',category:'Coat',season:'CW26',retailPrice:179,salePrice:179,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P48',type:'Manteco',brand:'Mango',name:'CAPPOTTO LANA MANTECO MAXI-REVERS',category:'Coat',season:'CW26',retailPrice:179,salePrice:114,markdownPct:36.3,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P49',type:'Manteco',brand:'Fortela',name:'Fortela Giacca Renny',category:'Jacket',season:'CW26',retailPrice:859,salePrice:510,markdownPct:40.6,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P50',type:'Control',brand:'H&M',name:'CAPPOTTO A MANTELLA IN MISTO LANA DOPPIATA',category:'Coat',season:'CW26',retailPrice:299,salePrice:299,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P51',type:'Control',brand:'H&M',name:'MAXI CAPPOTTO IN LANA CON COLLO SCIALLATO',category:'Coat',season:'CW26',retailPrice:279,salePrice:279,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P52',type:'Control',brand:'H&M',name:'CAPPOTTO OVERSIZE MISTO LANA',category:'Coat',season:'CW26',retailPrice:79.99,salePrice:79.99,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P53',type:'Control',brand:'COS',name:'CAPPOTTO DOPPIOPETTO LUNGO OVERSIZE IN LANA',category:'Coat',season:'FW25',retailPrice:299,salePrice:299,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P54',type:'Control',brand:'COS',name:'CAPPOTTO SARTORIALE IN TWILL DI LANA CON CINTURA',category:'Coat',season:'CW26',retailPrice:279,salePrice:279,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P55',type:'Control',brand:'Mango',name:'CAPPOTTO LANA DOPPIA ABBOTTONATURA',category:'Coat',season:'CW26',retailPrice:199.99,salePrice:89.99,markdownPct:55.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P56',type:'Control',brand:'Mango',name:'CAPPOTTO LANA REVERS',category:'Coat',season:'CW26',retailPrice:239.99,salePrice:199.99,markdownPct:16.7,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P57',type:'Control',brand:'Zara',name:'CAPPOTTO CORTO MISTO LANA CON COLLO ALTO',category:'Coat',season:'CW26',retailPrice:65.95,salePrice:45.95,markdownPct:30.3,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P58',type:'Control',brand:'Aritzia',name:'The Embrace Double-Faced Coat - Luxe (Re)Wool',category:'Coat',season:'CW26',retailPrice:458,salePrice:458,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P59',type:'Control',brand:'Fortela',name:'Scotland Giacca Classica In Lana A Quadri',category:'Jacket',season:'CW26',retailPrice:950,salePrice:950,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P60',type:'Control',brand:'Selected',name:'CAPPOTTO IN MISTO LANA',category:'Coat',season:'CW26',retailPrice:239.99,salePrice:239.99,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P61',type:'Control',brand:'Selected',name:'CAPPOTTO',category:'Coat',season:'CW26',retailPrice:189.99,salePrice:189.99,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
  {id:'P62',type:'Control',brand:'Zara',name:'ORIGINS WOOL JACKET WITH ZIP',category:'Coat',season:'CW26',retailPrice:149,salePrice:149,markdownPct:0.0,resalePrice:null,residualPct:null,fabric:'',url:'#'},
];

// ── Tier brand sets ────────────────────────────────────────────
const FAST_FASHION_BRANDS = new Set(['Zara','Mango','H&M','MANGO']);
const CONTEMPORARY_BRANDS = new Set(['COS','Woolrich','Fortela','Selected','SELECTED','Aritzia','Karen Millen','KarenMillen']);

let PAIRS = [
  // premiumPct in percentage units (e.g. 76.9 means +76.9%)
  {pairId:'PA01',brand:'Zara',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P09',controlId:'P10',mRetail:299,cRetail:169,premiumDollar:130,premiumPct:76.9},
  {pairId:'PA02',brand:'Zara',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P11',controlId:'P12',mRetail:229,cRetail:139,premiumDollar:90,premiumPct:64.7},
  {pairId:'PA03',brand:'Zara',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P19',controlId:'P20',mRetail:269,cRetail:99.95,premiumDollar:169.05,premiumPct:169.1},
  {pairId:'PA04',brand:'Zara',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P46',controlId:'P62',mRetail:179,cRetail:149,premiumDollar:30,premiumPct:20.1},
  {pairId:'PA05',brand:'Mango',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P01',controlId:'P55',mRetail:299.99,cRetail:199.99,premiumDollar:100,premiumPct:50.0},
  {pairId:'PA06',brand:'Mango',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P05',controlId:'P56',mRetail:329.99,cRetail:239.99,premiumDollar:90,premiumPct:37.5},
  {pairId:'PA07',brand:'Mango',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P08',controlId:'P13',mRetail:399,cRetail:199.99,premiumDollar:199.01,premiumPct:99.5},
  {pairId:'PA08',brand:'H&M',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P41',controlId:'P50',mRetail:249,cRetail:299,premiumDollar:-50,premiumPct:-16.7},
  {pairId:'PA09',brand:'H&M',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P42',controlId:'P51',mRetail:279,cRetail:279,premiumDollar:0,premiumPct:0.0},
  {pairId:'PA10',brand:'H&M',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P43',controlId:'P52',mRetail:149,cRetail:79.99,premiumDollar:69.01,premiumPct:86.3},
  {pairId:'PA11',brand:'COS',tier:'Contemporary Premium',category:'Coat',season:'FW25',mantecoId:'P33',controlId:'P53',mRetail:299,cRetail:299,premiumDollar:0,premiumPct:0.0},
  {pairId:'PA12',brand:'COS',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P34',controlId:'P54',mRetail:449,cRetail:279,premiumDollar:170,premiumPct:60.9},
  {pairId:'PA13',brand:'Woolrich',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P15',controlId:'P16',mRetail:1320,cRetail:295,premiumDollar:1025,premiumPct:347.5},
  {pairId:'PA14',brand:'Karen Millen',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P17',controlId:'P18',mRetail:188,cRetail:509,premiumDollar:-321,premiumPct:-63.1},
  {pairId:'PA15',brand:'Aritzia',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P29',controlId:'P58',mRetail:378,cRetail:458,premiumDollar:-80,premiumPct:-17.5},
  {pairId:'PA16',brand:'Fortela',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P07',controlId:'P59',mRetail:800,cRetail:950,premiumDollar:-150,premiumPct:-15.8},
  {pairId:'PA17',brand:'Selected',tier:'Contemporary Premium',category:'Coat',season:'FW25',mantecoId:'P02',controlId:'P60',mRetail:279.99,cRetail:239.99,premiumDollar:40,premiumPct:16.7},
  {pairId:'PA18',brand:'Selected',tier:'Contemporary Premium',category:'Coat',season:'CW26',mantecoId:'P44',controlId:'P61',mRetail:279,cRetail:189.99,premiumDollar:89.01,premiumPct:46.8},
  {pairId:'PA19',brand:'Zara',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P19',controlId:'P57',mRetail:269,cRetail:65.95,premiumDollar:203.05,premiumPct:307.9},
  {pairId:'PA20',brand:'Mango',tier:'Fast Fashion Premium',category:'Coat',season:'CW26',mantecoId:'P06',controlId:'P13',mRetail:349.99,cRetail:199.99,premiumDollar:150,premiumPct:75.0},
];

let MARKDOWN = [
  // 10 pairs with Manteco sale data. deltaPp = M MD% minus C MD% (negative = Manteco held price better)
  {pairId:'PA05',brand:'Mango',mRetail:299.99,mSale:179.99,mMdPct:40.0,cRetail:199.99,cSale:null,cMdPct:null,deltaPp:null,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA06',brand:'Mango',mRetail:329.99,mSale:249,mMdPct:24.5,cRetail:239.99,cSale:119,cMdPct:50.4,deltaPp:-25.9,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA07',brand:'Mango',mRetail:399,mSale:279,mMdPct:30.1,cRetail:199.99,cSale:99.99,cMdPct:50.0,deltaPp:-19.9,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA09',brand:'H&M',mRetail:279,mSale:195,mMdPct:30.1,cRetail:279,cSale:null,cMdPct:null,deltaPp:null,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA10',brand:'H&M',mRetail:149,mSale:119,mMdPct:20.1,cRetail:79.99,cSale:null,cMdPct:null,deltaPp:null,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA13',brand:'Woolrich',mRetail:1320,mSale:925,mMdPct:29.9,cRetail:295,cSale:149,cMdPct:49.5,deltaPp:-19.6,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA14',brand:'Karen Millen',mRetail:188,mSale:48,mMdPct:74.5,cRetail:509,cSale:305,cMdPct:40.1,deltaPp:34.4,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA15',brand:'Aritzia',mRetail:378,mSale:118,mMdPct:68.8,cRetail:458,cSale:null,cMdPct:null,deltaPp:null,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA17',brand:'Selected',mRetail:279.99,mSale:111.95,mMdPct:60.0,cRetail:239.99,cSale:null,cMdPct:null,deltaPp:null,mSaleUrl:'#',cSaleUrl:'#'},
  {pairId:'PA20',brand:'Mango',mRetail:349.99,mSale:149.99,mMdPct:57.1,cRetail:199.99,cSale:99.99,cMdPct:50.0,deltaPp:-7.1,mSaleUrl:'#',cSaleUrl:'#'},
];

let RESALE = [
  // 7 Manteco + 4 Control listings. residualPct in percentage units.
  {pairId:'PA03',side:'Manteco',platform:'Vinted',originalRetail:269,resalePrice:26.95,residualPct:10.0,age:'',condition:'Very Good',date:'',listingUrl:'#'},
  {pairId:'PA04',side:'Manteco',platform:'Vinted',originalRetail:179,resalePrice:47.95,residualPct:26.8,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA04',side:'Control',platform:'Vinted',originalRetail:149,resalePrice:50,residualPct:33.6,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA05',side:'Manteco',platform:'Vinted',originalRetail:299.99,resalePrice:158,residualPct:52.7,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA05',side:'Control',platform:'Vinted',originalRetail:199.99,resalePrice:77,residualPct:38.5,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA06',side:'Manteco',platform:'eBay',originalRetail:329,resalePrice:220,residualPct:66.9,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA06',side:'Control',platform:'Vinted',originalRetail:239.99,resalePrice:70,residualPct:29.2,age:'',condition:'Very Good',date:'',listingUrl:'#'},
  {pairId:'PA11',side:'Manteco',platform:'Vestiaire Collective',originalRetail:299,resalePrice:179,residualPct:59.9,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA11',side:'Control',platform:'Vinted',originalRetail:299,resalePrice:155,residualPct:51.8,age:'',condition:'Excellent',date:'',listingUrl:'#'},
  {pairId:'PA13',side:'Manteco',platform:'Vestiaire Collective',originalRetail:1320,resalePrice:611,residualPct:46.3,age:'',condition:'Very Good',date:'',listingUrl:'#'},
  {pairId:'PA15',side:'Manteco',platform:'eBay',originalRetail:378,resalePrice:100,residualPct:26.5,age:'',condition:'Very Good',date:'',listingUrl:'#'},
];"""

new_lines = [l + '\n' for l in real_data.split('\n')]

# Replace lines 600-720 (0-indexed 599-719)
result = lines[:599] + new_lines + lines[720:]

with open('manteco_dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f'Done. File now has {len(result)} lines.')

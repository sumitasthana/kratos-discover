-**:LLM provider -**DpsgFodrStu```
src/
├──li.py            # Cmman-linirf enry pit├──xcpon.y# Cusom xcpion clsss├──__init__.py
│
├──nodes/   Pipeline (Nodes 1-5)│├──preprocessor.py# N1: Par & Chk│├──schema_discveypy # N 2: SchmDiovry│├──cniec_g.py# Nod 3: Conence G│├──gxtrco.py#Node3.5:GRCCmptExtacti│└──atomizer/#Node4:RquremetAtomizr│├──ndep  #Mainatizr od│├──btchpossor.py│├──pmptbuir.y│├──espnsers.py│└──schemrpai.py
│├── eval/  5:Qualiy Evaluton│  ├──val_nod.py       # Mai evalun│   ├── clasfr.py   #Faurepattrlaifer│   ├── mdl.y     #vlrprml│   └── checks/     #Individualqualitychecks
│├──coverage.py
│├──testability.py
│├──grounding.py
│├──hallucination.py
│├──deduplication.py│└──schema_compliance.py
│
├──models/#Datamodels
│├──chunks.py#ContnChk,Prprocsor
│├── reqire.py    # RulatoryRequire,ExractionM│├──gr_cmpospy# Poc,sk, Contol copon│├──chma_map.py      # ShemaMap fr dscovereschemas│├──.py  # ha1Se(pipein tate)
│├── anical_schma.py#Cannial cha dfiiion
│├── shaed.y     # Shdum (RulType,RuleCgory)│└──control_metadata/#Controlenrichmentmodels
│├──models.py
│├──templates.py
│└──inference.py
│
├──scoring/#Confidencescoring│├──confidence_scorer.py#Mainscoringlogic
│├──grounding.py#Groundingclassification
│├──features.py#Featurecomputation
│└──verb_replacer.py#Vaguevbeplemen│├──par/              #Dcmtasr│   └──docx_prer.py   #DCXlgic
│├──/               # LLMppttela│├──omizr/          #Atomzp│  ├──grc_extrc/     #GRCopmpt│ └──shem_scvery/#Scmascovryprompts
│├──cache/#Cachingutilities
│└──schema_cache.py#Schemacaching
│
├──config/#Configurationfiles│└──gate_config.yaml#Confidencegatethresholds
│
└──utils/#Utilityfunctions
├──chunking.py# Tx chunkgtiiti   └── m_cl.py # Ahpcnwrapr```
##PpenArctuNode1: PrrcssorLcation`ns/ppor.py`PrsDOX dcmntsnourdhunks wihmadata.yhdf pr_an_chunk(fe_ph,fil_y,x_uk_hr,m_chun_car)-> PrprossorOutput```
`PrprocessorOtut` ontining`ContenChunk` objctNe 2: Schema DscvryLocatin`nodes/schema_discovy.py`

Analzesdocumn hunks ofer hehmasrucusg strified samplg.pythondef scha_dicvey_agnt(sta:ha1St)->dOutpt`ScmaMap`wthisvrdfeldhmas###No 3:CfieceGeLocaion`s/cofinc_ga.py`Mksccp/rvew/rjctdecsobad onschem fienc.def check_onfidce(sPhase1) ->GDcsn```

**Ou**`GaDci`h,cr,nheshld#Nd35:GC Exractornods/rc_xractorEsPocy,Ris,rolfrom able cunk.
GCComponExtractorNode_cal__sePhae1Satedc```

**Oupu**: `GRCCRspse` wipolicie,rsks, onrols
###No4: Aizr

**Locion**`odes/omizr/od.py`
Eomic rulory requirmswithconnccoring.

```pyhon
clssRquirmAomizerNod:_ll_Phas1dic
```
**Output**:Listo`ReulatoyReqimnt`object wih`ExrcionMadaNd 5: Eval Qualeval/eval_ndAxqaliywihmuplchck.
valqualiytePha1Sdic
```
**Oupu**: `EalRpot` wth quaiycoeanu fg## Coe Conens

###ae ManagemntTheieline us `Phas1Se` (TpdDct)o psda bewee nodes:
```yhonclassPhase1Ste(TypedDi,ta=Fale):
hks:li[CtnChk]
_mapSchemaMapeqirmentlistRegatoryRrme]xtac_metadataExtacMetadatagr_conns:GRCComnnsRsponeeval_porEvlRepotgae_dciionGaDisionRegulryRqum: rqiremntmwith-`eqiremnt` Uniqueidenifie(..,-DQ-ac034e)
- `r_yp`: Tpee(data_qaity_thrsholddoumetain_equemn,tc.)-``Extraced requiement text-`` Sourceext eference-``Conidence scre(-0)-``T-ficarbuwh`_cfidnfaus`###fnc SogMuli-iisngwh fau-`guing_mch:Jrdmary wthuc`letes`:Rqirdfd covrg`qaifiatoPcofmaubvl-`chmcolanc`:Smvlo-`cohc`:Intnasistcy-`dai_igl`: Domin-pcific indictoDOCX│
▼┌────────────────┐
│ Peprcssor│→CntChuk[]└───────┬────────┘
 │▼┌─────────────────┐
│chDvery│→Schap└───────┬────────┘│▼
┌─────────────────┐│ConfeGe│→GeDiion(acct/revew/reje)
└────────┬────────┘│▼┌─────────────────┐│GRCExtc│→Polics, Risks,Cotls
└────────┬────────┘│▼┌─────────────────┐│  Atmizr│ReguloryReqie[]
└────────┬────────┘│▼
┌─────────────────┐│EvalQuality│→EvRprt
└────────┬────────┘│ ▼
JSONOttwihcs. Nodeca btedndied inistion.Cofdc-FitEvryinclucficesci.w-confne iesre fgged fr humaview.Schm VadaionTy-specificttrbueschem ene cosistent output strutur.Auto-rpai attemptto fix ss.
###VAllextctosrevfd agassuceexttoent halcinas.Gndingcaat(EXAT/PARAPHRASE/INFERENCE) indictslibility.QuEvuaonCoprhensvqulycheckncu:Tbiliyasssm-Hallucecti-upii alyis-Schemaliacveiicaton#LI Infe```bashFullpipl
pyn cli.pyiz --ipuocx--r.jnPreprocessnlycliycss--nudocumen.dcxSchemdscveyythci.pydisc-sch--u.dcxCgra##GThh(`g/g_nigyl`mo_ccpt0.85Auo-cceptbthi
hmnviw:0.70Hevew bewenthsn uacept
arje0.50Auto-rjectbeowhi#Envim Varable```
ANTHRPIC_API_KEY=sk--...```
---

Seelo
-[has1-Par-an-Chk](Phae1-Ps-d-unk.md)-Prcea-[Phase1-ch-Dcovry-A](Pha1-ch-Dcvy-A.md)cm sv[hs1-CidceSc](Pha1ConfiScor.m)-ConfidengaPhse1-GRC-Exrctrhase1GC-Extator  GRCxtctin
-hase1-Atz-AgetPhas1-AtzAg.md RequimnzaoPh1-EvalPe1Eval.m-Quly valat
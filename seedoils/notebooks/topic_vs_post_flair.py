"""Validity check of the BERTopic topics against the post flair of the thread each comment sits in (from 2024, when 84% of posts are flaired).
NMI(topic, thread flair) against a null that shuffles flairs across threads; plus the topics most over-represented under each common flair (lift = share of the flair vs share overall).
Run from final_project/ with the NLP env: ./.venv-nlp/bin/python seedoils/notebooks/topic_vs_post_flair.py (paths below are relative to final_project/). Aggregates only."""
import gzip,json,collections,pandas as pd,numpy as np,datetime as dt
from sklearn.metrics import normalized_mutual_info_score as nmi
SPLIT=1704067200; R='seedoils/data/raw/'; PR='seedoils/data/processed/'
pf={}
for l in gzip.open(R+'StopEatingSeedOils_posts.jsonl.gz','rt'):
    try:d=json.loads(l)
    except: continue
    pf[d['id']]=d.get('link_flair_text')
lk={}; uf=collections.defaultdict(list)
for l in gzip.open(R+'StopEatingSeedOils_comments.jsonl.gz','rt'):
    try:d=json.loads(l)
    except: continue
    lk[d['id']]=d['link_id'][3:]
    f=d.get('author_flair_text')
    if f not in (None,'None',''): uf[f].append(int(d['created_utc']))
print('first appearance of user flairs:')
for f,ts in sorted(uf.items(),key=lambda x:-len(x[1]))[:12]:
    print(' ',f[:30].ljust(30),dt.datetime.fromtimestamp(min(ts),dt.timezone.utc).strftime('%Y-%m'),len(ts))
T=pd.read_csv(PR+'seso_doc_topics.csv.gz',usecols=['id','kind','created_utc','topic'])
T['link']=T.id.map(lk); T.loc[T.kind!='comment','link']=T.id
T['flair']=T.link.map(pf)
Tf=T[T.flair.notna()&(T.created_utc>=SPLIT)]
print('\nfrom 2024 docs with a thread flair:',len(Tf),'of',(T.created_utc>=SPLIT).sum())
print('NMI(topic, thread flair) =',round(nmi(Tf.topic,Tf.flair),3))
th=Tf.drop_duplicates('link')[['link','flair']].copy();rng=np.random.default_rng(0);nul=[]
for _ in range(20):
    th['s']=rng.permutation(th.flair.values);mp=dict(zip(th.link,th.s));nul.append(nmi(Tf.topic,Tf.link.map(mp)))
print('null NMI (flairs shuffled across threads):',round(np.mean(nul),3),'+-',round(np.std(nul),3))
I=pd.read_csv(PR+'seso_topics_info.csv').set_index('topic')
top=Tf.flair.value_counts().head(9).index
ct=pd.crosstab(Tf.topic,Tf.flair);base=ct.sum(axis=1)/ct.values.sum()
for f in top:
    col=ct[f];share=col/col.sum();lift=share/base
    t5=(share.where(col>=60)).sort_values(ascending=False).head(4)
    print(f'\n{f}  (n={col.sum()})')
    for t,s in t5.items(): print(f'   {s*100:4.1f}% topic {t} lift {lift[t]:.1f} | {I.loc[t,"top_words"][:55]}')

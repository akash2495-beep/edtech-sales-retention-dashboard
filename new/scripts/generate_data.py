"""Generate the synthetic EdTech sales funnel and retention dataset (Jan 2024 - Oct 2026).
Usage: pip install pandas numpy openpyxl, then python generate_data.py
Writes 9 CSV files into ../data. All data is synthetic; seed is fixed for reproducibility."""
import numpy as np, pandas as pd, os, zipfile
rng = np.random.default_rng(2026)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
os.makedirs(OUT, exist_ok=True)
START = pd.Timestamp('2024-01-01'); CUTOFF = pd.Timestamp('2026-10-31')
D = lambda n: pd.to_timedelta(n, unit='D')

first = ['Aarav','Vivaan','Aditya','Arjun','Rohan','Karthik','Rahul','Siddharth','Nikhil','Varun','Ananya','Diya','Priya','Sneha','Kavya','Meera','Pooja','Ishita','Neha','Divya','Harsha','Manoj','Suresh','Deepak','Ritu','Shreya','Tanvi','Akash','Vikram','Lakshmi','Yash','Pranav','Swati','Naveen','Bhavana','Mohit','Anjali','Sandeep','Rekha','Gaurav']
last = ['Sharma','Reddy','Nair','Iyer','Gowda','Patel','Singh','Kumar','Das','Menon','Rao','Joshi','Verma','Shetty','Bhat','Kulkarni','Mishra','Chatterjee','Pillai','Naidu','Gupta','Mehta','Jain','Hegde','Kapoor']
used = set()
def nm():
    while True:
        n = f"{rng.choice(first)} {rng.choice(last)}"
        if n not in used:
            used.add(n); return n

# ---------- dim_team ----------
teams = pd.DataFrame([
 ['T01','Team Phoenix','Sales','8'], ['T02','Team Titans','Sales','9'],
 ['T03','Team Spartans','Sales','10'], ['T04','Team Falcons','Sales','11-12'],
 ['T05','Retention Alpha','Retention','8-9'], ['T06','Retention Beta','Retention','10'],
 ['T07','Retention Gamma','Retention','11-12']],
 columns=['team_id','team_name','department','grades_handled'])
teams['team_manager'] = [nm() for _ in range(len(teams))]

# ---------- dim_mentor ----------
sizes = {'T01':6,'T02':10,'T03':10,'T04':8,'T05':6,'T06':6,'T07':5}
mrows = []; skill = {}; k = 1
for tid, size in sizes.items():
    for i in range(size):
        mid = f"M{k:03d}"; k += 1
        lead = (i == 0)
        if lead or rng.random() < 0.7:
            join = pd.Timestamp('2021-11-01') + D(int(rng.integers(0, 780)))
        else:
            join = START + D(int(rng.integers(0, 900)))
        ex = pd.NaT
        if not lead and rng.random() < 0.25:
            lo = max(join, START) + D(120); hi = CUTOFF - D(30)
            if lo < hi:
                ex = lo + D(int(rng.integers(0, (hi - lo).days)))
        mrows.append([mid, nm(), tid, 'Team Lead' if lead else 'Mentor', join, ex])
        skill[mid] = float(np.clip(rng.normal(1, 0.14), 0.72, 1.3))
mentors = pd.DataFrame(mrows, columns=['mentor_id','mentor_name','team_id','role','join_date','exit_date'])

def active_ids(team, a, b):
    m = mentors[mentors.team_id == team]
    x = m[(m.join_date <= a) & (m.exit_date.isna() | (m.exit_date >= b))]
    if len(x) == 0:
        x = m[(m.join_date <= b) & (m.exit_date.isna() | (m.exit_date >= a))]
    return x.mentor_id.values

# ---------- fact_leads ----------
src = ['Meta Ads','Google Ads','Organic','Referral','Webinar','Offline Event']
sp = [.32,.24,.15,.10,.11,.08]
src_mult = {'Meta Ads':.8,'Google Ads':.95,'Organic':1.0,'Referral':1.5,'Webinar':1.2,'Offline Event':1.1}
grade_mult = {8:.9,9:1.05,10:1.15,11:.95,12:1.0}
team_for_grade = {8:'T01',9:'T02',10:'T03',11:'T04',12:'T04'}
season = {1:1.0,2:1.05,3:1.35,4:1.45,5:1.4,6:1.1,7:.9,8:.85,9:1.0,10:1.15,11:1.0,12:.8}
sconv = {3:1.08,4:1.1,5:1.1,12:.92}
cities = ['Bengaluru','Hyderabad','Chennai','Pune','Mumbai','Delhi NCR','Kolkata','Ahmedabad','Jaipur','Kochi','Lucknow','Other']
cp = np.array([.16,.10,.10,.08,.10,.12,.06,.05,.04,.04,.03,.12]); cp /= cp.sum()

months = pd.period_range('2024-01','2026-10',freq='M')
parts = []
for i, p in enumerate(months):
    ms = p.start_time; me = min(p.end_time.normalize(), CUTOFF)
    n = int(1050*(1+0.008*i)*season[p.month]*rng.uniform(.95,1.05))
    dates = ms + D(rng.integers(0, (me-ms).days+1, n))
    g = rng.choice([8,9,10,11,12], n, p=[.15,.27,.28,.17,.13])
    df = pd.DataFrame({'lead_date':dates,'lead_source':rng.choice(src,n,p=sp),'grade':g,
        'board':rng.choice(['CBSE','ICSE','State Board'],n,p=[.55,.12,.33]),
        'city':rng.choice(cities,n,p=cp),'month_idx':i,'month':p.month})
    df['sales_mentor_id'] = ''
    for gr, t in team_for_grade.items():
        idx = df.index[df.grade == gr]
        ids = active_ids(t, ms, p.end_time.normalize())
        df.loc[idx, 'sales_mentor_id'] = rng.choice(ids, len(idx))
    parts.append(df)
L = pd.concat(parts).sort_values('lead_date').reset_index(drop=True)
N = len(L)
L['lead_id'] = [f"L{i+1:06d}" for i in range(N)]

connected = rng.random(N) < .82
booked = connected & (rng.random(N) < .55)
demo_date = L.lead_date + D(rng.integers(1, 7, N))
upcoming = booked & (demo_date > CUTOFF)
attended = booked & ~upcoming & (rng.random(N) < .72)
sk = L.sales_mentor_id.map(skill).values
cp_ = .35 * L.lead_source.map(src_mult).values * L.grade.map(grade_mult).values * sk \
      * L.month.map(lambda m: sconv.get(m,1.0)).values * (1 + .003*L.month_idx.values)
enrolled = attended & (rng.random(N) < np.clip(cp_, 0, .8))
enroll_date = (demo_date + D(rng.integers(0, 11, N))).clip(upper=CUTOFF)

status = np.select(
    [enrolled, attended, booked & ~upcoming, upcoming, connected],
    ['Enrolled','Demo Done - Not Converted','Demo No-Show','Demo Booked (Upcoming)','Demo Not Booked'],
    default='Not Connected')
L['first_call_connected'] = connected.astype(int)
L['demo_booked'] = booked.astype(int)
L['demo_date'] = demo_date.where(booked)
L['demo_attended'] = attended.astype(int)
L['enrolled'] = enrolled.astype(int)
L['lead_status'] = status
leads = L[['lead_id','lead_date','lead_source','grade','board','city','sales_mentor_id',
           'first_call_connected','demo_booked','demo_date','demo_attended','enrolled','lead_status']].copy()

# ---------- fact_enrollments ----------
E = L[enrolled].copy(); E['enrollment_date'] = enroll_date[enrolled].values
E = E.sort_values('enrollment_date').reset_index(drop=True)
E['enrollment_id'] = [f"E{i+1:05d}" for i in range(len(E))]
plan_m = np.zeros(len(E), int)
for j, g in enumerate(E.grade.values):
    plan_m[j] = rng.choice([6,12],p=[.55,.45]) if g == 12 else rng.choice([6,12,24],p=[.3,.5,.2])
E['plan_months'] = plan_m
E['plan_name'] = E.plan_months.map({6:'Foundation (6M)',12:'Annual (12M)',24:'Complete (24M)'})
base = E.plan_months.map({6:14000,12:25000,24:42000}) * E.grade.map({8:.9,9:1.0,10:1.1,11:1.2,12:1.25})
E['list_price_inr'] = (base/100).round().astype(int)*100
E['discount_pct'] = rng.choice([0,5,10,15,20,25], len(E), p=[.12,.2,.28,.2,.14,.06])
E['amount_paid_inr'] = (E.list_price_inr*(1-E.discount_pct/100)/100).round().astype(int)*100
E['payment_mode'] = rng.choice(['Full Payment','EMI'], len(E), p=[.55,.45])
enr = E[['enrollment_id','lead_id','enrollment_date','sales_mentor_id','grade','lead_source',
         'plan_name','plan_months','list_price_inr','discount_pct','amount_paid_inr','payment_mode']]

# ---------- fact_renewals ----------
R = E[['enrollment_id','lead_id','enrollment_date','grade','plan_months','amount_paid_inr','discount_pct']].copy()
R['renewal_due_date'] = R.enrollment_date + D((R.plan_months*30.44).round().astype(int))
R['att'] = np.clip(rng.beta(6,3,len(R))*100, 15, 100).round(1)
R['score'] = np.clip(rng.normal(62,14,len(R)), 10, 98).round(1)
R['tickets'] = rng.poisson(1.2, len(R))
R['doubts'] = rng.poisson(R.att/12).astype(int)
tmap = {8:'T05',9:'T05',10:'T06',11:'T07',12:'T07'}
rm = []
for g, due in zip(R.grade, R.renewal_due_date):
    ref = min(due, CUTOFF)
    ids = active_ids(tmap[g], ref, ref); rm.append(rng.choice(ids))
R['retention_mentor_id'] = rm
mat = R.renewal_due_date <= CUTOFF
plan_eff = R.plan_months.map({6:-.15,12:.1,24:.2})
gr_eff = R.grade.map({8:.1,9:.15,10:-.2,11:.05,12:-1.2})
trend = .18 * np.clip((R.renewal_due_date - pd.Timestamp('2024-06-01')).dt.days/365, 0, 2.5)
z = (-.1 + .045*(R.att-67) + .022*(R.score-62) - .22*R.tickets + plan_eff + gr_eff + trend
     - .01*R.discount_pct + .9*(R.retention_mentor_id.map(skill)-1) + rng.normal(0,.5,len(R)))
renew = mat & (rng.random(len(R)) < 1/(1+np.exp(-z)))
R['renewal_status'] = np.where(~mat,'Not Due Yet',np.where(renew,'Renewed','Churned'))
R['renewal_date'] = (R.renewal_due_date + D(rng.integers(-15, 11, len(R)))).where(renew)
R['renewal_date'] = R.renewal_date.clip(upper=CUTOFF)
R['renewal_amount_inr'] = (R.amount_paid_inr*rng.uniform(.9,1.1,len(R))/100).round().astype(int)*100
R.loc[~renew,'renewal_amount_inr'] = np.nan
reasons = ['Price / Affordability','Low Engagement','Result Dissatisfaction','Board Exam Focus Shift','Switched to Competitor','Mentor / Teacher Issue','Relocation / Other']
base_w = np.array([.24,.20,.17,.12,.13,.08,.06])
cr = []
for a, st in zip(R.att, R.renewal_status):
    if st != 'Churned': cr.append(None); continue
    w = base_w.copy()
    if a < 55: w[1] *= 2.2
    w /= w.sum(); cr.append(rng.choice(reasons, p=w))
R['churn_reason'] = cr
R = R.reset_index(drop=True)
R['renewal_id'] = [f"R{i+1:05d}" for i in range(len(R))]
ren = R[['renewal_id','enrollment_id','lead_id','retention_mentor_id','grade','plan_months','renewal_due_date',
         'renewal_status','renewal_date','renewal_amount_inr','churn_reason']].copy()
ren['attendance_pct'] = R.att; ren['avg_test_score'] = R.score
ren['support_tickets'] = R.tickets; ren['doubt_sessions'] = R.doubts

# ---------- fact_targets ----------
tr = []
cnt = L.assign(m=L.lead_date.dt.to_period('M').dt.start_time).groupby(['m','sales_mentor_id']).size().reset_index(name='n')
for _, r in cnt.iterrows():
    tr.append([r.m, r.sales_mentor_id, 'Sales', 'Enrollments', max(2, round(r.n*.12))])
rc = R.assign(m=R.renewal_due_date.dt.to_period('M').dt.start_time)
rc = rc[rc.m <= CUTOFF].groupby(['m','retention_mentor_id']).size().reset_index(name='n')
for _, r in rc.iterrows():
    tr.append([r.m, r.retention_mentor_id, 'Retention', 'Renewals', max(1, round(r.n*.55))])
targets = pd.DataFrame(tr, columns=['month_start','mentor_id','department','target_metric','target_value'])

# ---------- marketing spend ----------
cpl = {'Meta Ads':650,'Google Ads':800,'Organic':120,'Referral':300,'Webinar':450,'Offline Event':900}
ms_ = L.assign(m=L.lead_date.dt.to_period('M').dt.start_time).groupby(['m','lead_source']).size().reset_index(name='n')
ms_['spend_inr'] = (ms_.n*ms_.lead_source.map(cpl)*rng.uniform(.9,1.1,len(ms_))/100).round().astype(int)*100
spend = ms_.rename(columns={'m':'month_start'})[['month_start','lead_source','spend_inr']]

# ---------- dims ----------
dd = pd.DataFrame({'date': pd.date_range('2024-01-01','2026-12-31')})
dd['year']=dd.date.dt.year; dd['quarter']='Q'+dd.date.dt.quarter.astype(str)
dd['month_num']=dd.date.dt.month; dd['month_name']=dd.date.dt.month_name(); dd['month_short']=dd.date.dt.strftime('%b')
dd['year_month']=dd.date.dt.strftime('%Y-%m'); dd['week_of_year']=dd.date.dt.isocalendar().week.astype(int)
dd['day_name']=dd.date.dt.day_name(); dd['is_weekend']=(dd.date.dt.dayofweek>=5).astype(int)
dd['fiscal_year']=np.where(dd.month_num>=4,'FY'+dd.year.astype(str)+'-'+(dd.year+1).astype(str).str[2:],'FY'+(dd.year-1).astype(str)+'-'+dd.year.astype(str).str[2:])
dd['fiscal_quarter']='Q'+(((dd.month_num-4)%12)//3+1).astype(str)
dsrc = pd.DataFrame({'lead_source':src,'channel_type':['Paid','Paid','Organic','Referral','Event','Event']})
mentors['employment_status'] = np.where(mentors.exit_date.isna(),'Active','Exited')

# ---------- known data issues (leads only) ----------
lo = leads.copy()
i1 = rng.choice(lo.index, int(.012*len(lo)), replace=False)
lo.loc[i1,'lead_source'] = [rng.choice(['meta ads',' Google Ads','GOOGLE ADS','referral ','Webinar ']) for _ in i1]
bl = lo.index[(lo.city=='Bengaluru')]
lo.loc[rng.choice(bl, int(.08*len(bl)), replace=False),'city'] = 'Bangalore'
lo.loc[rng.choice(lo.index, int(.015*len(lo)), replace=False),'city'] = np.nan
lo = pd.concat([lo, lo.sample(60, random_state=1)]).sort_values('lead_id').reset_index(drop=True)

def save(df, name):
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_datetime64_any_dtype(d[c]): d[c] = d[c].dt.strftime('%Y-%m-%d')
    d.to_csv(f'{OUT}/{name}.csv', index=False)
for df, n in [(dd,'dim_date'),(teams,'dim_team'),(mentors,'dim_mentor'),(dsrc,'dim_lead_source'),
              (lo,'fact_leads'),(enr,'fact_enrollments'),(ren,'fact_renewals'),(targets,'fact_targets'),(spend,'fact_marketing_spend')]:
    save(df, n); print(n, len(df))

# ---------- diagnostics ----------
print('lead->enroll %', round(leads.enrolled.mean()*100,2))
print('connected', leads.first_call_connected.mean().round(3),'booked',leads.demo_booked.mean().round(3),'attended',leads.demo_attended.mean().round(3))
print(leads.groupby('grade').enrolled.mean().round(3).to_dict())
print(leads.groupby('lead_source').enrolled.mean().round(3).to_dict())
leads['yr']=leads.lead_date.dt.year; print(leads.groupby('yr').enrolled.mean().round(3).to_dict())
m = ren[ren.renewal_status!='Not Due Yet']; m=m.assign(yr=m.renewal_due_date.dt.year)
print('renewal rate', (m.renewal_status=='Renewed').mean().round(3)); print(m.groupby('yr').apply(lambda x:(x.renewal_status=='Renewed').mean()).round(3).to_dict()); print(m.groupby('grade').apply(lambda x:(x.renewal_status=='Renewed').mean()).round(3).to_dict())
print('mentors active', (mentors.employment_status=='Active').sum(), 'of', len(mentors))
print(enr.amount_paid_inr.describe().round(0).to_dict())

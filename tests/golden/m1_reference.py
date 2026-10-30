"""Case-specific Decimal worksheets, not a second general-purpose tax engine.

No production code/constants or generated engine results are imported. Equations,
source locators and validity ranges are in references/m1-acceptance.md. The inputs
are frozen in m1-cases.json; revise the derivations when changing those inputs.
"""
from decimal import Decimal as D, localcontext


def row(year, opening, closing, *, spending, tax=0, wages=0, taxable_wages=0,
        contributions=0, pension=0, ss=0, rmd=0, conversion=0, draws=None,
        gain=0, basis=0, paid=None, unmet=0, tax_fields=None, payroll=0):
    """Assemble reference identities only; never infer a tax or draw from actuals."""
    return dict(year=year, opening_accounts=opening, closing_accounts=closing,
        opening_total=sum(opening.values()), closing_total=sum(closing.values()),
        closing_total_real=sum(closing.values()), investment_growth_total=0,
        wages_gross=wages, wages_taxable=taxable_wages, pretax_contributions=contributions,
        pension_gross=pension, social_security_gross=ss, rmd_total=rmd, unmet_rmd=0,
        roth_converted=conversion, skipped_conversions=[], extra_draws=draws or {},
        ira_extra_taxable=(draws or {}).get('ira',0), realized_ltcg=gain,
        taxable_basis_end={'taxable':basis}, tax=tax_fields or {},
        payroll_tax={'total':payroll}, tax_due_total=tax, tax_paid=tax, unpaid_tax=0,
        living_expenses_due=spending, living_expenses_paid=spending if paid is None else paid,
        unmet_spending=unmet)


def retirement_transition():
    # Both spouses are 65 in 2027. One earns 120k with 10k pretax deferral.
    # Frozen MFJ standard + age deduction=32200+2*1650; extra deduction=12000
    # in 2027/28. First year taxable ordinary=110000-47500=62500.
    t1=D(2480)+D('.12')*(D(62500)-D(24800))
    fica=D(120000)*(D('.062')+D('.0145'))
    c1=D(10000)+D(110000)-D(80000)-t1-fica
    # 2028: D = 80000-c1-20000 + .10*(20000+D-47500).
    d2=(D(80000)-c1-D(20000)-D(2750))/D('.90')
    t2=d2-(D(80000)-c1-D(20000))
    assert 0 < D(20000)+d2-D(47500) < D(24800)
    # 2029: pension 20k + SS 36k, no enhanced senior deduction.
    # Taxable SS=.85*(20000+D+18000-44000)+6000=.85D+900.
    # T=2480+.12*(20000+D+.85D+900-35500-24800)=.222D-2248.
    # D=24000+T => .778D=21752. This is NOT the production iteration.
    d3=D(21752)/D('.778'); ss_taxable=D('.85')*d3+D(900)
    taxable3=D(20000)+d3+ss_taxable-D(35500); t3=d3-D(24000)
    assert D(24800)<taxable3<D(100800) and ss_taxable<D(30600)
    a0=dict(cash=D(10000),taxable=D(0),ira=D(500000),roth=D(0),**{'401k':D(0)})
    a1={**a0,'cash':c1,'401k':D(10000)}
    a2={**a1,'cash':D(0),'ira':a1['ira']-d2}
    a3={**a2,'ira':a2['ira']-d3}
    specs=[(2027,a0,a1,t1,fica,D(110000),D(47500),D(12000),D(0),{},D(0),D(0)),
           (2028,a1,a2,t2,D(0),D(20000)+d2,D(47500),D(12000),D(0),{'ira':d2},D(20000),D(0)),
           (2029,a2,a3,t3,D(0),D(20000)+d3+ss_taxable,D(35500),D(0),ss_taxable,{'ira':d3},D(20000),D(36000))]
    rows=[]
    for year,a,b,t,f,agi,ded,enh,st,draws,pension,ss in specs:
        rows.append(row(year,a,b,spending=80000,tax=t+f,wages=120000 if year==2027 else 0,
            taxable_wages=110000 if year==2027 else 0,contributions=10000 if year==2027 else 0,
            pension=pension,ss=ss,draws=draws,payroll=f,
            tax_fields=dict(adjusted_gross_income=agi,gross_ordinary=agi,
                taxable_social_security=st,standard_plus_age_deduction=35500,
                enhanced_senior_deduction=enh,deduction_total=ded,ordinary_taxable=agi-ded,
                ordinary_tax=t,capital_gains_tax=0,federal_income_tax=t,niit_due=0)))
    return dict(rows=rows,failed=False,first_failure_year=None)


def rmd_conversion_niit():
    opening=dict(cash=D(10000),taxable=D(500000),ira=D(1060000),roth=D(0))
    rows=[]
    for year,divisor,conversion in [(2027,D('26.5'),D(200000)),(2028,D('25.5'),D(100000))]:
        rmd=opening['ira']/divisor
        ordinary=rmd+conversion; taxable=ordinary-D(18150)
        # Hand selected segments, with range checks; no production bracket loop.
        if year==2027:
            assert D(201775)<taxable<D(256225)
            ot=D(41024)+D('.32')*(taxable-D(201775))
            # MAGI excess > NII: NIIT=.038*(draw/2).
            draw=(D(180000)-opening['cash']-rmd+ot)/D('.906')
            niit_base=draw/2
        else:
            assert D(105700)<taxable<D(201775)
            ot=D(17966)+D('.24')*(taxable-D(105700))
            # MAGI excess < NII: NIIT=.038*(ordinary+draw/2-200000).
            draw=(D(180000)-rmd+ot+D('.038')*(ordinary-D(200000)))/D('.906')
            niit_base=ordinary+draw/2-D(200000)
        gain=draw/2; agi=ordinary+gain
        assert agi>D(175000)  # enhanced senior deduction fully phased out
        assert D(49450)<taxable and taxable+gain<D(545500) # all gains at 15%
        assert 0<draw<opening['taxable'] and 0<niit_base<=gain
        assert (agi-D(200000)>=gain) == (year==2027)
        cg=D('.15')*gain; niit=D('.038')*niit_base; tax=ot+cg+niit
        closing=dict(cash=D(0),taxable=opening['taxable']-draw,
                     ira=opening['ira']-rmd-conversion,roth=opening['roth']+conversion)
        expected=row(year,opening,closing,spending=180000,tax=tax,rmd=rmd,conversion=conversion,
            draws={'taxable':draw},gain=gain,basis=closing['taxable']/2,
            tax_fields=dict(gross_ordinary=ordinary,taxable_social_security=0,
                adjusted_gross_income=agi,standard_plus_age_deduction=18150,
                enhanced_senior_deduction=0,deduction_total=18150,ordinary_taxable=taxable,
                long_term_gain_taxable=gain,ordinary_tax=ot,capital_gains_tax=cg,
                income_tax_method='stacked_capital_gains',federal_income_tax=ot+cg,
                niit_magi_assumed_equal_agi=agi,niit_net_investment_income=gain,
                niit_threshold=200000,niit_tax_base=niit_base,niit_due=niit,
                total_federal_income_and_niit=tax))
        expected['rmd']=[dict(account='ira',age=year-1954,previous_dec31_balance=opening['ira'],
            divisor=divisor,required=rmd,taken=rmd,unmet=0)]
        expected['conversion_transfers']=[dict(**{'from':'ira','to':'roth'},amount=conversion)]
        rows.append(expected); opening=closing
    return dict(rows=rows,failed=False,first_failure_year=None)


def account_depletion():
    a0=dict(cash=D(10000),taxable=D(20000),ira=D(40000),roth=D(5000))
    a1={**a0,'cash':D(0),'taxable':D(0)}
    # In 2027 the 10k gain is absorbed by unused standard deduction.
    # 2028 D=30000+1240+.12*(D-16100-12400) => .88D=27820.
    draw=D(27820)/D('.88'); tax=draw-D(30000)
    assert D(12400)<draw-D(16100)<D(50400)
    a2={**a1,'ira':D(40000)-draw}
    empty={key:D(0) for key in a2}; paid=a2['ira']+a2['roth']
    rows=[row(2027,a0,a1,spending=30000,draws={'taxable':D(20000)},gain=10000,
              tax_fields=dict(adjusted_gross_income=10000,ordinary_taxable=0,long_term_gain_taxable=0,federal_income_tax=0,niit_due=0)),
          row(2028,a1,a2,spending=30000,tax=tax,draws={'ira':draw},
              tax_fields=dict(adjusted_gross_income=draw,ordinary_taxable=draw-D(16100),long_term_gain_taxable=0,federal_income_tax=tax,niit_due=0)),
          row(2029,a2,empty,spending=30000,draws={'ira':a2['ira'],'roth':a2['roth']},paid=paid,unmet=D(30000)-paid,
              tax_fields=dict(adjusted_gross_income=a2['ira'],ordinary_taxable=0,federal_income_tax=0,niit_due=0)),
          row(2030,empty,empty,spending=30000,paid=0,unmet=30000,
              tax_fields=dict(adjusted_gross_income=0,ordinary_taxable=0,federal_income_tax=0,niit_due=0))]
    return dict(rows=rows,failed=True,first_failure_year=2029)


def growth_indexing():
    # Single, born 1966: works in 2027 (age 61), retired in 2028 (age 62).
    # Plan inflation 3% escalates spending/deferral; the HYPOTHETICAL bracket
    # index is 2%. Portfolio return 6%-1% fee=5%; cash yield 2%.
    infl={2027:D('1.03'),2028:D('1.03')**2}
    index={2027:D('1.02'),2028:D('1.02')**2}
    r=D('.05')
    def grow(accounts):
        return {k:v*(D('.02') if k=='cash' else r) for k,v in accounts.items()}
    def tops(year):
        return [D(t)*index[year] for t in (12400,50400,105700,201775)]
    wages=D(220000)*D('1.05'); deferral=D(20000)*infl[2027]
    assert deferral<=min(wages,D(24500)*index[2027])
    a0=dict(cash=D(20000),taxable=D(50000),ira=D(300000),roth=D(0),**{'401k':D(0)})
    growth1=grow(a0); interest1=growth1['cash']
    # 2027: ordinary taxable income sits in the indexed 24% bracket.
    ordinary1=wages-deferral+interest1
    deduction1=D(16100)*index[2027]
    taxable1=ordinary1-deduction1
    t=tops(2027)
    assert t[2]<taxable1<t[3]
    ordinary_tax1=D('.10')*t[0]+D('.12')*(t[1]-t[0])+D('.22')*(t[2]-t[1])+D('.24')*(taxable1-t[2])
    # Published 2027 OASDI cap; Additional Medicare above 200,000 single.
    oasdi1=D(192300)*D('.062'); medicare1=wages*D('.0145'); extra1=(wages-D(200000))*D('.009')
    payroll1=oasdi1+medicare1+extra1
    # A 60,000 real one-time expense forces a partial sale of the appreciated
    # account: gain fraction g=1-30,000/52,500. Each gain dollar bears 15%
    # (taxable income is above the indexed 0% zone; ordinary rates would be 24%)
    # plus 3.8% NIIT, because MAGI exceeds 200,000 by more than NII.
    value1=a0['taxable']+growth1['taxable']; g=1-D(30000)/value1
    living1=(D(120000)+D(60000))*infl[2027]
    cash1=a0['cash']+interest1+wages-deferral
    sale1=(living1+ordinary_tax1+payroll1+D('.038')*interest1-cash1)/(1-(D('.15')+D('.038'))*g)
    gain1=g*sale1
    assert 0<sale1<value1 and D(49450)*index[2027]<taxable1 and taxable1+gain1<t[3]
    assert ordinary1-D(200000)>=interest1  # NIIT base is all NII
    niit1=D('.038')*(interest1+gain1); gains_tax1=D('.15')*gain1
    tax1=ordinary_tax1+gains_tax1+niit1+payroll1
    basis1=D(30000)-sale1*D(30000)/value1
    a1={k:a0[k]+growth1[k] for k in a0}
    a1.update(cash=cash1+sale1-tax1-living1,taxable=value1-sale1,**{'401k':a1['401k']+deferral})
    assert abs(a1['cash'])<D('.00001')
    a1['cash']=D(0)
    # 2028: no wages or cash interest. The whole taxable balance is sold, then
    # IRA draw D solves D = spending - V2 + T with ordinary income in the
    # indexed 22% bracket and all realized gain at 15% (below the 22% cap).
    growth2=grow(a1)
    value2=a1['taxable']+growth2['taxable']; gain2=value2-basis1
    living2=D(120000)*infl[2028]
    deduction2=D(16100)*index[2028]
    t=tops(2028)
    base_tax=D('.10')*t[0]+D('.12')*(t[1]-t[0])
    draw2=(living2-value2+base_tax-D('.22')*(deduction2+t[1])+D('.15')*gain2)/D('.78')
    taxable2=draw2-deduction2
    assert value2<living2 and t[1]<taxable2 and taxable2+gain2<t[2] and D(49450)*index[2028]<taxable2
    assert draw2+gain2<D(200000) and draw2<a1['ira']+growth2['ira']
    ordinary_tax2=base_tax+D('.22')*(taxable2-t[1]); gains_tax2=D('.15')*gain2
    tax2=ordinary_tax2+gains_tax2
    a2={k:a1[k]+growth2[k] for k in a1}
    a2.update(taxable=D(0),ira=a2['ira']-draw2)
    rows=[]
    for year,opening,closing,growth,tax,fields in (
        (2027,a0,a1,growth1,tax1,dict(wages=wages,taxable_wages=wages-deferral,contributions=deferral,
            spending=living1,draws={'taxable':sale1},gain=gain1,basis=basis1,payroll=payroll1)),
        (2028,a1,a2,growth2,tax2,dict(spending=living2,draws={'taxable':value2,'ira':draw2},gain=gain2,
            basis=D(0),payroll=D(0)))):
        expected=row(year,opening,closing,tax=tax,**fields)
        expected.update(market_return=r,inflation_factor=infl[year],growth_by_account=growth,
            investment_growth_total=sum(growth.values()),
            closing_total_real=sum(closing.values())/infl[year],rmd=[],conversion_transfers=[])
        rows.append(expected)
    rows[0]['tax']=dict(gross_ordinary=ordinary1,adjusted_gross_income=ordinary1+gain1,
        standard_plus_age_deduction=deduction1,enhanced_senior_deduction=0,deduction_total=deduction1,
        ordinary_taxable=taxable1,long_term_gain_taxable=gain1,ordinary_tax=ordinary_tax1,
        capital_gains_tax=gains_tax1,income_tax_method='stacked_capital_gains',
        federal_income_tax=ordinary_tax1+gains_tax1,niit_net_investment_income=interest1+gain1,
        niit_tax_base=interest1+gain1,niit_due=niit1,rule_multiplier=index[2027],taxable_social_security=0)
    rows[0]['payroll_tax']=dict(wage_base_per_person=D(192300),social_security_tax=oasdi1,
        medicare_tax=medicare1,additional_medicare_tax=extra1,total=payroll1)
    rows[1]['tax']=dict(gross_ordinary=draw2,adjusted_gross_income=draw2+gain2,
        standard_plus_age_deduction=deduction2,enhanced_senior_deduction=0,deduction_total=deduction2,
        ordinary_taxable=taxable2,long_term_gain_taxable=gain2,ordinary_tax=ordinary_tax2,
        capital_gains_tax=gains_tax2,income_tax_method='stacked_capital_gains',
        federal_income_tax=tax2,niit_net_investment_income=gain2,niit_tax_base=0,niit_due=0,
        rule_multiplier=index[2028],taxable_social_security=0)
    # 2028 has no wages; the hypothetical cap still indexes the published 2027 cap.
    rows[1]['payroll_tax']=dict(wage_base_per_person=D(192300)*index[2027],total=0)
    return dict(rows=rows,failed=False,first_failure_year=None)


def taxable_record(q, nq, interest, cgd, proceeds, ratio):
    sold=proceeds*ratio
    return dict(gain_treatment='long_term_proportional_with_distributions',qualified_dividends=q,
        nonqualified_dividends=nq,interest=interest,capital_gain_distributions=cgd,
        reinvested_distributions=q+nq+interest+cgd,sale_proceeds=proceeds,basis_sold=sold,
        sale_gain_or_loss=proceeds-sold)


def taxable_distributions_carryover():
    # Single, born 1957 (70 in 2027), pension 40,000 and no wages or SS; frozen
    # 2026 tables; 25% return, no inflation. Deductions 16,100+2,050+6,000 senior.
    deduction=D(24150)
    v0,b0=D(200000),D(260000)
    r=D('.25')
    # 2027: distributions on the 200,000 opening balance, reinvested into basis.
    q1,nq1,i1,c1=v0*D('.02'),v0*D('.005'),v0*D('.01'),v0*D('.005')
    value1=v0*(1+r); basis1=b0+q1+nq1+i1+c1; ratio1=basis1/value1
    assert ratio1>1  # every sale realizes a loss
    # Assume the 3,000 limit binds; AGI is then fixed and taxable income sits in the 12% bracket.
    agi1=D(40000)+i1+nq1+q1-D(3000)
    ordinary_taxable1=D(40000)+i1+nq1-D(3000)-deduction
    assert D(12400)<ordinary_taxable1<D(50400) and ordinary_taxable1+q1<D(49450)  # dividends at 0%
    tax1=D(1240)+D('.12')*(ordinary_taxable1-D(12400))
    sale1=D(60000)+tax1-D(40000)
    net1=sale1-sale1*ratio1+c1-D(5000)
    assert net1<-3000  # the limit binds, as assumed
    adjusted1=agi1-deduction+D(3000)+D(6000)
    assert adjusted1>D(3000)  # all 3,000 used
    carry1=-net1-D(3000)
    a1=dict(cash=D(0),taxable=value1-sale1); basis_end1=basis1-sale1*ratio1
    # 2028: the 25% return lifts value above basis, so the sale realizes a gain
    # that the carryover reduces; qualified dividends and net gain stay at 0%.
    v1=a1['taxable']
    q2,nq2,i2,c2=v1*D('.02'),v1*D('.005'),v1*D('.01'),v1*D('.005')
    value2=v1*(1+r); basis2=basis_end1+q2+nq2+i2+c2; ratio2=basis2/value2
    assert ratio2<1
    ordinary2=D(40000)+i2+nq2; ordinary_taxable2=ordinary2-deduction
    assert D(12400)<ordinary_taxable2<D(50400)
    tax2=D(1240)+D('.12')*(ordinary_taxable2-D(12400))
    sale2=D(60000)+tax2-D(40000)
    net2=sale2-sale2*ratio2+c2-carry1
    preferential2=q2+net2; agi2=ordinary2+preferential2
    assert net2>0 and ordinary_taxable2+preferential2<D(49450) and agi2<D(75000)
    a2=dict(cash=D(0),taxable=value2-sale2); basis_end2=basis2-sale2*ratio2
    rows=[]
    for year,a,b,growth,tax,sale,ratio,dist,basis_end,fields in (
        (2027,dict(cash=D(0),taxable=v0),a1,v0*r,tax1,sale1,ratio1,(q1,nq1,i1,c1),basis_end1,dict(
            gross_ordinary=D(40000)+i1+nq1,adjusted_gross_income=agi1,capital_loss_carryover_in=D(5000),
            net_capital_gain_or_loss=net1,capital_loss_deduction=D(3000),capital_gain_or_loss_in_agi=D(-3000),
            preferential_income=q1,ordinary_taxable=ordinary_taxable1,long_term_gain_taxable=q1,
            capital_loss_adjusted_taxable_income=adjusted1,capital_loss_used=D(3000),capital_loss_carryover_out=carry1,
            niit_net_investment_income=i1+nq1+q1-D(3000))),
        (2028,a1,a2,v1*r,tax2,sale2,ratio2,(q2,nq2,i2,c2),basis_end2,dict(
            gross_ordinary=ordinary2,adjusted_gross_income=agi2,capital_loss_carryover_in=carry1,
            net_capital_gain_or_loss=net2,capital_loss_deduction=D(0),capital_gain_or_loss_in_agi=net2,
            preferential_income=preferential2,ordinary_taxable=ordinary_taxable2,long_term_gain_taxable=preferential2,
            capital_loss_adjusted_taxable_income=None,capital_loss_used=D(0),capital_loss_carryover_out=D(0),
            niit_net_investment_income=i2+nq2+q2+net2))):
        q,nq,i,c=dist
        expected=row(year,a,b,spending=60000,tax=tax,pension=40000,draws={'taxable':sale},
            gain=sale-sale*ratio,basis=basis_end,tax_fields=dict(fields,taxable_account_interest=i,
                nonqualified_dividends=nq,qualified_dividends=q,capital_gain_distributions=c,
                standard_plus_age_deduction=D(18150),enhanced_senior_deduction=D(6000),deduction_total=deduction,
                ordinary_tax=tax,capital_gains_tax=0,income_tax_method='stacked_capital_gains',
                federal_income_tax=tax,niit_tax_base=0,niit_due=0))
        expected.update(growth_by_account=dict(cash=D(0),taxable=growth),investment_growth_total=growth,
            closing_total_real=sum(b.values()),
            taxable_accounts={'taxable':taxable_record(q,nq,i,c,sale,ratio)})
        rows.append(expected)
    return dict(rows=rows,failed=False,first_failure_year=None)


def taxable_niit_loss_limit():
    # Single, 50 in 2027, wages 300,000; zero returns. Dividends and interest
    # on 500,000 reinvested into 600,000 basis; every sale realizes a loss.
    v,b=D(500000),D(600000)
    q,interest=v*D('.03'),v*D('.01')
    basis=b+q+interest; ratio=basis/v
    agi=D(300000)+interest+q-D(3000)        # the 3,000 limit binds (checked below)
    ordinary_taxable=D(300000)+interest-D(3000)-D(16100)
    assert D(256225)<ordinary_taxable<D(640600)
    ordinary_tax=D(58448)+D('.35')*(ordinary_taxable-D(256225))
    assert ordinary_taxable>D(49450) and ordinary_taxable+q<D(545500)
    gains_tax=D('.15')*q                     # 15% stacking is below the 35% ordinary rate
    nii=interest+q-D(3000)                   # Form 8960 lines 1, 2 and 5a
    assert agi-D(200000)>nii
    niit=D('.038')*nii
    payroll=D(192300)*D('.062')+D(300000)*D('.0145')+(D(300000)-D(200000))*D('.009')
    tax=ordinary_tax+gains_tax+niit+payroll
    sale=tax                                 # wages exactly cover living expenses
    loss=sale*ratio-sale
    assert loss>D(3000)
    adjusted=agi-D(16100)+D(3000)
    assert adjusted>D(3000)
    closing=dict(cash=D(0),taxable=v-sale)
    expected=row(2027,dict(cash=D(0),taxable=v),closing,spending=300000,tax=tax,wages=300000,
        taxable_wages=300000,draws={'taxable':sale},gain=-loss,basis=basis-sale*ratio,payroll=payroll,
        tax_fields=dict(gross_ordinary=D(300000)+interest,adjusted_gross_income=agi,
            taxable_account_interest=interest,nonqualified_dividends=0,qualified_dividends=q,
            capital_gain_distributions=0,capital_loss_carryover_in=0,net_capital_gain_or_loss=-loss,
            capital_loss_deduction=D(3000),capital_gain_or_loss_in_agi=D(-3000),preferential_income=q,
            standard_plus_age_deduction=D(16100),enhanced_senior_deduction=0,deduction_total=D(16100),
            ordinary_taxable=ordinary_taxable,long_term_gain_taxable=q,ordinary_tax=ordinary_tax,
            capital_gains_tax=gains_tax,income_tax_method='stacked_capital_gains',
            federal_income_tax=ordinary_tax+gains_tax,capital_loss_adjusted_taxable_income=adjusted,
            capital_loss_used=D(3000),capital_loss_carryover_out=loss-D(3000),
            niit_magi_assumed_equal_agi=agi,niit_net_investment_income=nii,niit_tax_base=nii,niit_due=niit,
            total_federal_income_and_niit=ordinary_tax+gains_tax+niit))
    expected['payroll_tax']=dict(wage_base_per_person=D(192300),total=payroll)
    expected['taxable_accounts']={'taxable':taxable_record(q,D(0),interest,D(0),sale,ratio)}
    return dict(rows=[expected],failed=False,first_failure_year=None)


def references():
    with localcontext() as ctx:
        ctx.prec=40
        return {'retirement-transition':retirement_transition(),
                'rmd-conversion-niit':rmd_conversion_niit(),
                'account-depletion':account_depletion(),
                'growth-indexing':growth_indexing(),
                'taxable-distributions-carryover':taxable_distributions_carryover(),
                'taxable-niit-loss-limit':taxable_niit_loss_limit()}

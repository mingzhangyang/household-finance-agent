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


def references():
    with localcontext() as ctx:
        ctx.prec=40
        return {'retirement-transition':retirement_transition(),
                'rmd-conversion-niit':rmd_conversion_niit(),
                'account-depletion':account_depletion()}

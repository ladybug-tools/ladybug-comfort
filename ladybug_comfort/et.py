# -*- coding: utf-8 -*-
"""Effective temperature transitioned from legacy code of @stgeorges"""

def effective_temperature(Ta, ws, rh, SR, ac):
    # inputs: (Ta, ws, rh, SR, ac):
    if ws <= 0.2:
        # formula by Missenard
        TE = Ta - 0.4*(Ta - 10)*(1-rh/100)
    elif ws > 0.2:
        # modified formula by Gregorczuk (WMO, 1972; Hentschel, 1987)
        TE = 37 - ( (37-Ta)/(0.68-(0.0014*rh)+(1/(1.76+1.4*(ws**0.75)))) ) - (0.29 * Ta * (1-0.01*rh))
    
    # Radiative-effective temperature
    TRE = TE + ((1 - 0.01*ac)*SR) * ((0.0155 - 0.00025*TE) - (0.0043 - 0.00011*TE))
    
    if TRE < 1:
        effectTE = -4
        comfortable = 0
    elif TRE >= 1 and TE < 9:
        effectTE = -3
        comfortable = 0
    elif TRE >= 9 and TE < 17:
        effectTE = -2
        comfortable = 0
    elif TRE >= 17 and TE < 21:
        effectTE = -1
        comfortable = 0
    elif TRE >= 21 and TE < 23:
        effectTE = 0
        comfortable = 1
    elif TRE >= 23 and TE < 27:
        effectTE = 1
        comfortable = 0
    elif TRE >= 27:
        effectTE = 2
        comfortable = 0
    
    return TRE, effectTE, comfortable, []
    
    
    
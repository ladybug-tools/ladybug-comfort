# coding=utf-8
"""Utility functions for calculating Physiologic Equivalent Temperature (PET)."""
from __future__ import division

import math

from ladybug.rootfinding import secant_three_var

# constants for standard conditions
TC_SET = 36.6  # standard core body temperature
TSK_SET = 34  # standard skin temperature
TBODY_SET = 0.1 * TSK_SET + 0.9 * TC_SET  # weighted average for full-body temperature
# universal constants
P_REF = 101325  # sea-level barometric pressure [Pa]
C_AIR = 1010  # air specific heat capacity [J/kg-K]
L_VAP = 2420000  # latent heat of evaporation [J/Kg]
C_B = 3640  # blood specific heat [J/kg-K]
EM_SK = 0.99  # human skin emissivity
EM_CL = 0.95  # clothing emissivity
SIGM = 5.67 * (10 ** -8)  # Stefan-Boltzmann constant [W/(m2-K^(-4))]


def physiologic_equivalent_temperature(
        ta, tr, vel, rh, met, clo, age=36, sex=0.5, ht=1.65, m_body=62, pos='standing',
        b_press=101325):
    """Calculate Physiological Equivalent Temperature (PET).

    This method is based on Peter Hoeppe's original PET Fortran code, from the
    VDI Norm 3787, Blatt 2 [1][2], as well as Djordje Spasic's Ladybug Legacy
    source code. It includes the corrected reference environment and updated
    vapor transfer model published by Edouard Walther (AREP, France) and
    Quentin Goestchel (ENS Paris-Saclay, France) [3].

    Chris Mackey added support for the specification of metabolic rates in met
    (instead of Watts above basal metabolism) using a USDA report that relates
    Resting Metabolic Rate (RMR) (assumed to be 1 met) to Basal Metabolic
    Rate (BMR) using a Physical Activity Level (PAL) ratio [4].

    Note:
        [1] Hoeppe, Peter. (1999). "The physiological equivalent temperature - A
        universal index for the biometeorological assessment of the thermal
        environment." International journal of biometeorology. 43. 71-5.
        10.1007/s004840050118.
        https://link.springer.com/article/10.1007/s004840050118

        [2] Hoeppe, Peter. (2008). "Urban climatic map and standards for wind
        environment - Feasibility study, Technical Input Report No.1", The
        Chinese University of Hong Kong, Planning Department.

        [3] Walther, Edouard and Goestchel, Quentin. (2018). "The P.E.T. comfort
        index: Questioning the model". Building and Environment. 137C. 1-10.
        10.1016/j.buildenv.2018.03.054.
        https://www.sciencedirect.com/science/article/pii/S0360132318301896

        [4] "Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat,
        Fatty Acids, Cholesterol, Protein, and Amino Acids (Macronutrients) (2005)".
        USDA. National Academy of Sciences, Institute of Medicine, Food and
        Nutrition Board. Archived from the original on 10 March 2016.
        Chapter 12, page 8.
        https://web.archive.org/web/20160310031719/http://fnic.nal.usda.gov/\
        dietary-guidance/dri-nutrient-reports/energy-carbohydrate-fiber-fat-\
        fatty-acids-cholesterol-protein

    Args:
        ta: Air temperature [C].
        tr: Mean radiant temperature [C].
        vel: Relative air velocity [m/s].
        rh: Relative humidity [%].
        met: Metabolic rate [met]. Note that the original PET model requires that
            the activity of the human subject be accounted for as additional Watts
            above the basal metabolism, which is often difficult to estimate.
            In order to accept an input in [met], it is assumed that 1 met refers
            to Resting Metabolic Rate (RMR) and this is 1.17 times the male
            Basal Metabolic Rate (BMR) or 1.22 times the female BMR, where 1.17 =
            1 / 0.9 (TEF or food digestion) / 0.95 (basal to resting activity difference)
        clo: Clothing [clo].
        age: The age of the human subject in years. (Default: 36 years for middle age
            of the average worldwide life expectancy).
        sex: A value between 0 and 1 to indicate the sex of the human subject,
            which influences the computation of basal metabolism. 0 indicates male.
            1 indicates female and any number in between denotes a weighted average
            between the two. (Default: 0.5).
        ht: The height of the human subject in meters. (Default: 1.65m for
            a worldwide average between male and female height).
        m_body: The body mass of the human subject in kilograms. (Default: 62 kg
            for the worldwide average adult human body mass).
        pos: Text to indicate the posture of the human subject's body. Choose from
            the following: "standing", "seated", "crouching". (Default: "standing").
        b_press: An optional number for the air pressure in which the human subject
            exists, which determines the rate of sweat evaporation [Pa]. Default
            is pressure at sea level (101325 Pa).

    Returns:
        A dictionary containing results of the PET model with the following keys

        -   pet -- Physiological equivalent temperature (PET) [C]
        -   t_core -- Core body temperature [C]
        -   t_skin -- Skin temperature [C]
        -   t_clo -- Clothing temperature [C]
    """
    # find a steady state solution to the MEMI model balance under the input conditions
    t_min = (35, -10, -40)  # hypothermia conditions
    t_max = (41, 60, 64)  # hyperthermia conditions
    epsilon = 0.01  # the acceptable error in the result of the load balance
    conditions=(ta, tr, vel, rh, met, clo, age, sex, ht, m_body, pos)
    tn = secant_three_var(
        t_min, t_max, memi_balance, epsilon, other_args=conditions)

    # compute the PET using the human subject temperatures using a bisect method
    def f(tx):
        """A function with the input variables of the PET reference situation."""
        return memi_balance(tn, tx, tx, 0.1, 50, met, 0.9,
                            age, sex, ht, m_body, pos, b_press, False, True)
    ti = t_min[-1]  # start of the search interval
    tf = t_max[-1]  # end of the search interval
    pet = 0
    while tf - ti > epsilon:  # Dichotomy loop
        if f(ti) * f(pet) < 0:
            tf = pet
        else:
            ti = pet
        pet = (ti + tf) / 2.0

    # put all of the results into a single dictionary
    return {'pet': pet, 't_core': tn[0], 't_skin': tn[1], 't_clo': tn[2]}


def memi_balance(
        t_human, ta, tr, vel, rh, met, clo, age, sex, ht, m_body, pos,
        b_press=101325, actual=True, scalar=False):
    """Perform the human load balance using Munich energy balance model (MEMI).

    Args:
        t_human: A list of three values for the temperature of the human subject.

            * core body temperature [C]
            * skin temperature [C]
            * clothing temperature [C]

        ta: Air temperature [C].
        tr: Mean radiant temperature [C].
        vel: Relative air velocity [m/s].
        rh: Relative humidity [%].
        met: Metabolic rate [met].
        clo: Clothing [clo].
        age: The age of the human subject [years].
        sex: A value between 0 and 1 to indicate the sex of the human [0=male, 1=female].
        ht: The height of the human subject in [m].
        m_body: The body mass of the human subject in [kg].
        pos: Text for the posture of the human subject. [standing, seated, crouching].
        b_press: The barometric air pressure [Pa]. (Default: 101325 for sea level).
        actual: A boolean to indicate whether the calculation should be performed
            in the actual environment (True) or the reference environment (False).
        scalar: A boolean for whether the result should be returned as a vector of
            the energy flux across [core, skin, clo] or it should be a single scalar
            energy flux for the entire human subject.

    Returns:
        The energy flux across the entire human subject if scalar is True or a
        vector with energy flux across [core, skin, clo] if scalar is False.
    """
    # unpack the array of temperatures of the human subject
    t_core, t_sk, t_clo = t_human

    # compute tha area parameters of the body
    adu = 0.203 * m_body ** 0.425 * ht ** 0.725  # Dubois surface area of human subject
    feff = 0.725 if pos in ('standing', 'crouching') else 0.696  # radiant efficiency

    # increase the Burton surface to account for clothing, k = 0.31 for Hoeppe
    fcl = 1 + (0.31 * clo)  # increase heat exchange surface depending on clothing level
    facl = (173.51 * clo - 2.36 - 100.76 * clo * clo + 19.28 * clo ** 3.0) / 100
    a_clo = adu * facl + adu * (fcl - 1.0)
    a_effr = adu * feff  # effective radiative area derived from posture of the subject

    # partial pressure of water depending on relative humidity and air temperature
    if actual:  # the calculation of the actual vapor pressure of inputs
        vpa = rh / 100.0 * 6.105 * math.exp(17.27 * ta / (237.7 + ta))  # [hPa]
    else:  # use reference temperature, humidity and barometric pressure
        vpa = 12  # [hPa] vapour pressure of the standard environment

    # convection coefficient depending on air speed and subject posture
    if pos == 'standing':
        hc = 2.67 + (6.5 * vel ** 0.67)
    elif pos == 'seated':
        hc = 2.26 + (7.42 * vel ** 0.67)
    elif pos == 'crouching':
        hc = 8.6 * (vel ** 0.513)
    # modification of hc with the total air pressure
    hc = hc * (b_press / P_REF) ** 0.55

    # compute base metabolism for men and women in [W]
    r_fem = ht * 100.0 / m_body ** (1.0 / 3.0) - 42.1
    metab_female = 3.19 * m_body ** 0.75 * (1.0 + 0.004 * (30.0 - age) + 0.018 * r_fem)
    r_mal = ht * 100.0 / m_body ** (1.0 / 3.0) - 43.4
    metab_male = 3.45 * m_body ** 0.75 * (1.0 + 0.004 * (30.0 - age) + 0.01 * r_mal)
    # compute the total metabolism, accounting for the activity level
    if actual:  # actual human subject metabolic rate
        mec = (metab_male * 1.17 * met) / adu  # [W/m2]
        fec = (metab_female * 1.22 * met) / adu  # [W/m2]
    else:  # reference human subject metabolic rate assumes 80 W of activity level
        mec = (80 + metab_male) / adu  # [W/m2]
        fec = (80 + metab_female) / adu  # [W/m2]

    # attribution of internal energy depending on the sex of the subject
    he = ((1 - sex) * mec) + (sex * fec)  # [W/m2]

    # compute the respiratory energy losses
    texp = 0.47 * ta + 21.0  # [degC]
    dventpulm = he * 1.44 * (10.0 ** -6)  # pulmonary flow rate
    eres = C_AIR * (ta - texp) * dventpulm  # sensible heat loss [W/m2]
    vpexp = 6.11 * 10.0 ** (7.45 * texp / (235.0 + texp))
    p_hpa = b_press / 100  # barometric pressure [hPa]
    erel = 0.623 * L_VAP / p_hpa * (vpa - vpexp) * dventpulm  # latent heat loss [W/m2]
    ere = eres + erel  # total respiratory heat loss [W/m2]

    # compute the clothed fraction of the body and the clothing thickness
    rcl = clo / 6.45  # convert [clo] to [m2-K/W]
    if facl > 1.0:  # ensure that clothing does not cover more than 100%
        facl = 1.0
    y = 0  # thickness of the clothing layer
    if clo >= 2.0:
        y = 1.0
    elif clo > 0.6:
        y = (ht - 0.2) / ht
    elif clo > 0.3:
        y = 0.5
    elif clo > 0.0:
        y = 0.1

    # compute subject radius depending on the clothing level (6.28 = 2 * pi)
    r2 = adu * (fcl - 1.0 + facl) / (6.28 * ht * y)  # external radius
    r1 = facl * adu / (6.28 * ht * y)  # internal radius
    di = r2 - r1

    # compute the equivalent thermal resistance of body tissues
    alpha = 0.1  # constant in steady state model but updates t_body in transient model
    t_body = alpha * t_sk + (1 - alpha) * t_core
    htcl = (6.28 * ht * y * di) / (rcl * math.log(r2 / r1) * a_clo)  # [W/(m2-K)]

    # compute sweat losses
    qmsw = sweat_volume(t_body)
    # L_VAP / 1000 --> [J/g] ; qwsw / 3600 --> [g/m2-s]
    esw = (L_VAP / 1000) * (qmsw / 3600)  # [W/m2]
    # saturation vapor pressure at temperature tsk
    pv_sk = 6.105 * math.exp((17.27 * (t_sk + 273.15) - 4717.03) / (237.7 + t_sk))  # hPa
    # compute vapour transfer
    lw = 1.67  # Lewis factor [K/hPa]
    he_diff = hc * lw  # diffusion coefficient of air layer
    fecl = 1 / (1 + 0.92 * hc * rcl)  # Burton efficiency factor
    emax = he_diff * fecl * (pv_sk - vpa)  # maximum diffusion at skin surface
    w = esw / emax  # skin wettedness
    if w > 1:
        w = 1
        delta = esw - emax
        if delta < 0:
            esw = emax
    if esw < 0:
        esw = 0
    i_m = 0.38  # Woodcock's ratio
    r_ecl = (1 / (fcl * hc) + rcl) / (lw * i_m)  # clothing vapour transfer resistance
    ediff = (1 - w) * (pv_sk - vpa) / r_ecl  # diffusion heat transfer
    evap = -(ediff + esw)  # [W/m2]

    # compute radiation losses
    tr_k, tsk_k, tclo_k = tr + 273.15, t_sk + 273.15, t_clo + 273.15
    # for bare skin area:
    rbare = a_effr * (1.0 - facl) * EM_SK * SIGM * (tr_k ** 4 - tsk_k ** 4) / adu  # W/m2
    # for dressed area:
    rclo = feff * a_clo * EM_CL * SIGM * (tr_k ** 4 - tclo_k ** 4) / adu  # W/m2

    # compute convection losses #
    # for bare skin area:
    cbare = hc * (ta - t_sk) * adu * (1.0 - facl) / adu  # [W/m2]
    # for dressed area:
    cclo = hc * (ta - t_clo) * a_clo / adu  # [W/m2]

    # return either the calculated [core, skin, clo] energy flux or the scalar sum
    if scalar:  # return the scalar sum of the energy balance
        return he + ere + rclo + rbare + cclo + cbare + evap
    else:  # produce a vector of 3 energy fluxes across [core, skin, clo]
        vaso_ex = (vaso_circulation(t_core, t_sk) / 3600 * C_B + 5.28) * (t_core - t_sk)
        clo_ex = htcl * (t_sk - t_clo)
        e_core = he + ere - vaso_ex  # core balance [W/m2]
        e_sk = rbare + cbare + evap + vaso_ex - clo_ex  # skin balance [W/m2]
        e_clo = cclo + rclo + clo_ex  # clothes balance [W/m2]
        return (e_core, e_sk, e_clo)


def vaso_circulation(t_core, t_skin):
    """Calculate skin blood flow (vaso-circulation) using core and skin temperatures.

    Args:
        t_core: The core temperature of the human subject. [C].
        t_skin: The skin temperature of the human subject. [C].

    Returns:
         A number for the volume of blood flow in L/m2-h.
    """
    # set value signals
    sig_skin = TSK_SET - t_skin
    sig_core = t_core - TC_SET
    if sig_core < 0:  # t_core < TC_SET --> the blood flow is reduced
        sig_core = 0
    if sig_skin < 0:  # t_skin > TSK_SET --> the blood flow is increased
        sig_skin = 0
    # 6.3 L/m2-h is the standard volume of the blood flow
    qm_blood = (6.3 + 75 * sig_core) / (1 + 0.5 * sig_skin)
    return qm_blood if qm_blood < 90 else 90  # 90 L/m2-h is the blood flow upper limit


def sweat_volume(t_body):
    """Calculate skin sweat volume using average body temperatures.

    Args:
        t_body: The average body temperature of the human subject. [C].

    Returns:
         A number for the volume of sweat in g/m2-h.
    """
    sig_body = t_body - TBODY_SET
    if sig_body < 0:  # Tbody < Tbody_set --> The sweat flow is 0
        sig_body = 0
    qm_sw = 304.94 * 10 ** -3 * sig_body
    return qm_sw if qm_sw < 500 else 500  # 500 g/m2-h is the upper limit of sweat rate

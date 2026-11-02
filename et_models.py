"""
et_models.py - Shared endurance time (ET / MHT) model library.

Extracted verbatim from SETT (streamlit-rohmert-calculatorv8.py, v1.5.1) so the
Static Endurance Time Tool and the Static Rest Allowance Tool (SRAT) share one source of truth.
All equation functions take fMVC (0-1) and return endurance time in MINUTES.
Copyright Ryan C. A. Foley 2025
"""
import numpy as np


# Curve colors for different equations
CURVE_COLORS = {
    # Primary recommended model
    'Frey-Law & Avin 2010 (General)': '#003C71',
    # Joint-specific Frey-Law models
    'Frey-Law & Avin 2010 (Shoulder)': '#E75D2A',
    'Frey-Law & Avin 2010 (Elbow)': '#2E86AB',
    'Frey-Law & Avin 2010 (Trunk)': '#6A994E',
    'Frey-Law & Avin 2010 (Hand/Grip)': '#A23B72',
    'Frey-Law & Avin 2010 (Knee)': '#F18F01',
    'Frey-Law & Avin 2010 (Ankle)': '#BC4B51',
    # General models from literature
    'Rohmert 1960': '#8B5CF6',
    'Monod & Scherrer 1965': '#EC4899',
    'Huijgens 1981': '#14B8A6',
    'Sato et al. 1984 (General)': '#C73E1D',
    'Manenica 1986 (General)': '#84CC16',
    'Sjogaard 1986': '#0EA5E9',
    'Rose et al. 1992 (General)': '#5B8E7D',
    # Shoulder models
    'Sato et al. 1984 (Shoulder)': '#FF6B6B',
    'Rohmert et al. 1986 (Shoulder)': '#4ECDC4',
    'Mathiassen & Ahsberg 1999 (Shoulder)': '#45B7D1',
    'Garg et al. 2002 (Shoulder)': '#F7DC6F',
    # Elbow models
    'Hagberg 1981 (Elbow)': '#BB8FCE',
    'Manenica 1986 (Elbow)': '#85C1E9',
    'Sato et al. 1984 (Elbow)': '#F8B500',
    'Rohmert et al. 1986 (Elbow)': '#58D68D',
    'Rose et al. 2000 (Elbow)': '#EC7063',
    'Rose et al. 1992 (Elbow)': '#AF7AC5',
    # Hand/Grip models
    'Manenica 1986 (Hand Grip)': '#5DADE2',
    # Back/Hip models
    'Manenica 1986 (Body Pull)': '#48C9B0',
    'Manenica 1986 (Body Torque)': '#F5B041',
    'Manenica 1986 (Back)': '#EB984E',
    'Rohmert et al. 1986 (Back 1)': '#7DCEA0',
    'Rohmert et al. 1986 (Back 2)': '#D4AC0D',
    'Rohmert et al. 1986 (Back 3)': '#CD6155'
}


def get_recommended_equation():
    """Returns the default recommended equation (Frey-Law & Avin 2010 General)"""
    
    def frey_law_avin_2010_general(fmvc):
        """
        General maximum endurance time equation from Frey-Law & Avin (2010)
        Returns time in MINUTES
        
        Meta-analysis across 194 studies, N=3157 subjects
        Published equation: MET(sec) = 21.92 × F^(-1.98)
        """
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            # Original published coefficients (output is in SECONDS)
            COEF_A = 21.92
            COEF_B = -1.98
            SECONDS_TO_MINUTES = 1/60
            
            met_seconds = COEF_A * (fmvc ** COEF_B)
            met_minutes = met_seconds * SECONDS_TO_MINUTES
            return max(met_minutes, 0)
        except:
            return np.nan
    
    return {
        'Frey-Law & Avin 2010 (General)': frey_law_avin_2010_general
    }


def get_joint_specific_equations():
    """
    Returns joint-specific equations from Frey-Law & Avin (2010)
    All return time in MINUTES
    
    Original published coefficients output SECONDS, converted to MINUTES here.
    Coefficients from meta-analysis across 194 studies.
    """
    equations = {}
    
    # Conversion factor (published equations output seconds)
    SECONDS_TO_MINUTES = 1/60
    
    # Shoulder - N=176 subjects
    # Published: MET(sec) = 14.86 × F^(-1.83)
    def shoulder(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 14.86
            COEF_B = -1.83
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Shoulder)'] = shoulder
    
    # Elbow - N=838 subjects
    # Published: MET(sec) = 17.98 × F^(-2.21)
    def elbow(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 17.98
            COEF_B = -2.21
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Elbow)'] = elbow
    
    # Trunk - N=307 subjects
    # Published: MET(sec) = 22.69 × F^(-2.27)
    def trunk(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 22.69
            COEF_B = -2.27
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Trunk)'] = trunk
    
    # Hand/Grip - N=754 subjects
    # Published: MET(sec) = 33.55 × F^(-1.61)
    def hand_grip(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 33.55
            COEF_B = -1.61
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Hand/Grip)'] = hand_grip
    
    # Knee - N=875 subjects
    # Published: MET(sec) = 19.38 × F^(-1.88)
    def knee(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 19.38
            COEF_B = -1.88
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Knee)'] = knee
    
    # Ankle - N=207 subjects
    # Published: MET(sec) = 34.71 × F^(-2.06)
    def ankle(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            COEF_A = 34.71
            COEF_B = -2.06
            met_seconds = COEF_A * (fmvc ** COEF_B)
            return max(met_seconds * SECONDS_TO_MINUTES, 0)
        except:
            return np.nan
    equations['Frey-Law & Avin 2010 (Ankle)'] = ankle
    
    return equations


def get_literature_equations():
    """
    Returns ET-intensity models from the literature.
    All return time in MINUTES.
    
    Models from El ahrache et al. (2006) Table 1, plus additional sources.
    Organized by: General, Shoulder, Elbow, Hand/Grip, Back/Hip
    """
    equations = {}
    
    # =========================================================================
    # GENERAL MODELS (7 models)
    # =========================================================================
    
    # Rohmert 1960 - Original equation
    def rohmert_1960(fmvc):
        if fmvc <= 0.15 or fmvc >= 1:
            return np.nan
        try:
            # Corrected coefficient: 2.1 (not 21)
            result = -1.5 + 2.1/fmvc - 0.6/(fmvc**2) + 0.1/(fmvc**3)
            return max(result, 0)
        except:
            return np.nan
    equations['Rohmert 1960'] = rohmert_1960
    
    # Monod & Scherrer 1965
    def monod_scherrer_1965(fmvc):
        if fmvc <= 0.14:
            return np.nan
        try:
            return 0.4167 * ((fmvc - 0.14) ** -2.4)
        except:
            return np.nan
    equations['Monod & Scherrer 1965'] = monod_scherrer_1965
    
    # Huijgens 1981
    def huijgens_1981(fmvc):
        if fmvc <= 0.15 or fmvc >= 1:
            return np.nan
        try:
            numerator = 1 - fmvc
            denominator = fmvc - 0.15
            if denominator <= 0 or numerator <= 0:
                return np.nan
            ratio = numerator / denominator
            if ratio <= 0:
                return np.nan
            return 0.865 * (ratio ** (1/1.4))
        except:
            return np.nan
    equations['Huijgens 1981'] = huijgens_1981
    
    # Sato et al. 1984 (General)
    def sato_1984_general(fmvc):
        if fmvc <= 0.04:
            return np.nan
        try:
            return 0.3802 * ((fmvc - 0.04) ** -1.44)
        except:
            return np.nan
    equations['Sato et al. 1984 (General)'] = sato_1984_general
    
    # Manenica 1986 (General)
    def manenica_1986_general(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 14.88 * np.exp(-4.48 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (General)'] = manenica_1986_general
    
    # Sjogaard 1986
    def sjogaard_1986(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.2997 * (fmvc ** -2.14)
        except:
            return np.nan
    equations['Sjogaard 1986'] = sjogaard_1986
    
    # Rose et al. 1992 (General)
    def rose_1992_general(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 7.96 * np.exp(-4.16 * fmvc)
        except:
            return np.nan
    equations['Rose et al. 1992 (General)'] = rose_1992_general
    
    # =========================================================================
    # SHOULDER MODELS (4 models)
    # =========================================================================
    
    # Sato et al. 1984 (Shoulder)
    def sato_1984_shoulder(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.398 * (fmvc ** -1.29)
        except:
            return np.nan
    equations['Sato et al. 1984 (Shoulder)'] = sato_1984_shoulder
    
    # Rohmert et al. 1986 (Posture 1 - Shoulder)
    def rohmert_1986_posture1(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.2955 * (fmvc ** -1.658)
        except:
            return np.nan
    equations['Rohmert et al. 1986 (Shoulder)'] = rohmert_1986_posture1
    
    # Mathiassen & Ahsberg 1999
    def mathiassen_ahsberg_1999(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 40.6094 * np.exp(-9.7 * fmvc)
        except:
            return np.nan
    equations['Mathiassen & Ahsberg 1999 (Shoulder)'] = mathiassen_ahsberg_1999
    
    # Garg et al. 2002
    def garg_2002(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.5618 * (fmvc ** -1.7551)
        except:
            return np.nan
    equations['Garg et al. 2002 (Shoulder)'] = garg_2002
    
    # =========================================================================
    # ELBOW MODELS (6 models)
    # =========================================================================
    
    # Hagberg 1981
    def hagberg_1981(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.298 * (fmvc ** -2.14)
        except:
            return np.nan
    equations['Hagberg 1981 (Elbow)'] = hagberg_1981
    
    # Manenica 1986 (Elbow)
    def manenica_1986_elbow(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 20.6972 * np.exp(-4.5 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (Elbow)'] = manenica_1986_elbow
    
    # Sato et al. 1984 (Elbow)
    def sato_1984_elbow(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.195 * (fmvc ** -2.52)
        except:
            return np.nan
    equations['Sato et al. 1984 (Elbow)'] = sato_1984_elbow
    
    # Rohmert et al. 1986 (Posture 2 - Elbow)
    def rohmert_1986_posture2(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.2285 * (fmvc ** -1.391)
        except:
            return np.nan
    equations['Rohmert et al. 1986 (Elbow)'] = rohmert_1986_posture2
    
    # Rose et al. 2000
    def rose_2000(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 20.6 * np.exp(-6.04 * fmvc)
        except:
            return np.nan
    equations['Rose et al. 2000 (Elbow)'] = rose_2000
    
    # Rose et al. 1992 (Elbow)
    def rose_1992_elbow(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 10.23 * np.exp(-4.69 * fmvc)
        except:
            return np.nan
    equations['Rose et al. 1992 (Elbow)'] = rose_1992_elbow
    
    # =========================================================================
    # HAND/GRIP MODELS (1 model)
    # =========================================================================
    
    # Manenica 1986 (Hand grip)
    def manenica_1986_hand(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 16.6099 * np.exp(-4.5 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (Hand Grip)'] = manenica_1986_hand
    
    # =========================================================================
    # BACK/HIP MODELS (6 models)
    # =========================================================================
    
    # Manenica 1986 (Body pull)
    def manenica_1986_body_pull(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 27.6604 * np.exp(-4.2 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (Body Pull)'] = manenica_1986_body_pull
    
    # Manenica 1986 (Body torque)
    def manenica_1986_body_torque(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 12.4286 * np.exp(-4.3 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (Body Torque)'] = manenica_1986_body_torque
    
    # Manenica 1986 (Back muscles)
    def manenica_1986_back(fmvc):
        if fmvc <= 0 or fmvc > 1:
            return np.nan
        try:
            return 32.7859 * np.exp(-4.9 * fmvc)
        except:
            return np.nan
    equations['Manenica 1986 (Back)'] = manenica_1986_back
    
    # Rohmert et al. 1986 (Posture 3 - Back/Hip)
    def rohmert_1986_posture3(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 0.3001 * (fmvc ** -2.803)
        except:
            return np.nan
    equations['Rohmert et al. 1986 (Back 1)'] = rohmert_1986_posture3
    
    # Rohmert et al. 1986 (Posture 4 - Back/Hip)
    def rohmert_1986_posture4(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 1.2301 * (fmvc ** -1.308)
        except:
            return np.nan
    equations['Rohmert et al. 1986 (Back 2)'] = rohmert_1986_posture4
    
    # Rohmert et al. 1986 (Posture 5 - Back/Hip)
    def rohmert_1986_posture5(fmvc):
        if fmvc <= 0:
            return np.nan
        try:
            return 3.2613 * (fmvc ** -1.256)
        except:
            return np.nan
    equations['Rohmert et al. 1986 (Back 3)'] = rohmert_1986_posture5
    
    return equations


def get_all_equations():
    """Returns all equations combined"""
    all_eq = {}
    all_eq.update(get_recommended_equation())
    all_eq.update(get_joint_specific_equations())
    all_eq.update(get_literature_equations())
    return all_eq


def get_equation_info():
    """Returns information about each equation for display"""
    return {
        # Frey-Law models
        'Frey-Law & Avin 2010 (General)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'General/All muscles',
            'valid_range': '0-100% MVC',
            'notes': 'Recommended default model - meta-analysis across 194 studies, N=3157 subjects. Published: MET(sec) = 21.92 × F^(-1.98)'
        },
        'Frey-Law & Avin 2010 (Shoulder)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Shoulder muscles (deltoids)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=176 subjects. Published: MET(sec) = 14.86 × F^(-1.83)'
        },
        'Frey-Law & Avin 2010 (Elbow)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Elbow muscles (biceps, triceps)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=838 subjects. Published: MET(sec) = 17.98 × F^(-2.21)'
        },
        'Frey-Law & Avin 2010 (Trunk)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Trunk muscles (erector spinae)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=307 subjects. Published: MET(sec) = 22.69 × F^(-2.27)'
        },
        'Frey-Law & Avin 2010 (Hand/Grip)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Forearm flexors (grip)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=754 subjects. Published: MET(sec) = 33.55 × F^(-1.61)'
        },
        'Frey-Law & Avin 2010 (Knee)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Knee extensors (quadriceps)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=875 subjects. Published: MET(sec) = 19.38 × F^(-1.88)'
        },
        'Frey-Law & Avin 2010 (Ankle)': {
            'citation': 'Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. Ergonomics, 53(1), 109-129.',
            'muscle': 'Ankle plantarflexors (gastrocnemius, soleus)',
            'valid_range': '0-100% MVC',
            'notes': 'Meta-analysis, N=207 subjects. Published: MET(sec) = 34.71 × F^(-2.06)'
        },
        # General models from El ahrache et al. 2006
        'Rohmert 1960': {
            'citation': 'Rohmert, W. (1960). Ermittlung von Erholungspausen für statische Arbeit des Menschen. Internationale Zeitschrift für angewandte Physiologie einschließlich Arbeitsphysiologie, 18(2), 123-164.',
            'muscle': 'General',
            'valid_range': '15-100% MVC',
            'notes': 'Original foundational equation for static muscle endurance. N=38 subjects.'
        },
        'Monod & Scherrer 1965': {
            'citation': 'Monod, H., & Scherrer, J. (1965). The work capacity of a synergic muscular group. Ergonomics, 8(3), 329-338.',
            'muscle': 'General (synergistic groups)',
            'valid_range': '>14% MVC',
            'notes': 'Based on critical power concept'
        },
        'Huijgens 1981': {
            'citation': 'Huijgens, J.M.M.A. (1981). A model for quantifying static load, incorporating muscle fatigue. In Biomechanics Symposium, ASME, pp. 97-99.',
            'muscle': 'General',
            'valid_range': '15-100% MVC',
            'notes': 'Modified Rohmert equation using data from Rohmert (1960)'
        },
        'Sato et al. 1984 (General)': {
            'citation': 'Sato, H., Ohashi, J., Iwanaga, K., Yoshitake, R., & Shimada, K. (1984). Endurance time and fatigue in static contractions. Journal of Human Ergology, 13, 147-154.',
            'muscle': 'General',
            'valid_range': '>4% MVC',
            'notes': 'N=5 subjects'
        },
        'Manenica 1986 (General)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'General',
            'valid_range': '0-100% MVC',
            'notes': 'Exponential decay model. N=18 subjects.'
        },
        'Sjogaard 1986': {
            'citation': 'Sjogaard, G. (1986). Intramuscular changes during long-term contraction. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 136-143.',
            'muscle': 'General',
            'valid_range': '>0% MVC',
            'notes': 'Power law relationship, constructed from Rohmert (1960) and Hagberg (1981) data'
        },
        'Rose et al. 1992 (General)': {
            'citation': 'Rose, L., Ericsson, M., Glimskär, B., Nordgren, B., & Örtengren, R. (1992). Ergo-Index: Development of a model to determine pause needs after fatigue and pain reactions during work. In Computer Applications in Ergonomics, Elsevier, pp. 461-468.',
            'muscle': 'General',
            'valid_range': '0-100% MVC',
            'notes': 'Exponential decay model. N=8 subjects.'
        },
        # Shoulder models
        'Sato et al. 1984 (Shoulder)': {
            'citation': 'Sato, H., Ohashi, J., Iwanaga, K., Yoshitake, R., & Shimada, K. (1984). Endurance time and fatigue in static contractions. Journal of Human Ergology, 13, 147-154.',
            'muscle': 'Shoulder',
            'valid_range': '>0% MVC',
            'notes': 'Shoulder-specific model. N=5 subjects.'
        },
        'Rohmert et al. 1986 (Shoulder)': {
            'citation': 'Rohmert, W., Wangenheim, M., Mainzer, J., Zipp, P., & Lesser, W. (1986). A study stressing the need for a static postural force model for work analysis. Ergonomics, 29(10), 1235-1249.',
            'muscle': 'Shoulder (Posture 1)',
            'valid_range': '>0% MVC',
            'notes': 'Posture 1 - shoulder task. N=7 subjects.'
        },
        'Mathiassen & Ahsberg 1999 (Shoulder)': {
            'citation': 'Mathiassen, S.E. & Ahsberg, E. (1999). Prediction of shoulder flexion endurance from personal factors. International Journal of Industrial Ergonomics, 24, 315-329.',
            'muscle': 'Shoulder flexors',
            'valid_range': '0-100% MVC',
            'notes': 'Shoulder flexion specific. N=40 subjects.'
        },
        'Garg et al. 2002 (Shoulder)': {
            'citation': 'Garg, A., Hegmann, K.T., Schwoerer, B.J., & Kapellusch, J.M. (2002). The effect of maximum voluntary contraction on endurance times for the shoulder girdle. International Journal of Industrial Ergonomics, 30, 103-113.',
            'muscle': 'Shoulder girdle',
            'valid_range': '>0% MVC',
            'notes': 'Power law relationship. N=12 subjects.'
        },
        # Elbow models
        'Hagberg 1981 (Elbow)': {
            'citation': 'Hagberg, M. (1981). Muscular endurance and surface electromyogram in isometric and dynamic exercise. Journal of Applied Physiology, 51, 1-7.',
            'muscle': 'Elbow flexors',
            'valid_range': '>0% MVC',
            'notes': 'Elbow flexion. N=9 subjects.'
        },
        'Manenica 1986 (Elbow)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'Elbow',
            'valid_range': '0-100% MVC',
            'notes': 'Elbow-specific exponential model. N=18 subjects.'
        },
        'Sato et al. 1984 (Elbow)': {
            'citation': 'Sato, H., Ohashi, J., Iwanaga, K., Yoshitake, R., & Shimada, K. (1984). Endurance time and fatigue in static contractions. Journal of Human Ergology, 13, 147-154.',
            'muscle': 'Elbow',
            'valid_range': '>0% MVC',
            'notes': 'Elbow-specific model. N=5 subjects.'
        },
        'Rohmert et al. 1986 (Elbow)': {
            'citation': 'Rohmert, W., Wangenheim, M., Mainzer, J., Zipp, P., & Lesser, W. (1986). A study stressing the need for a static postural force model for work analysis. Ergonomics, 29(10), 1235-1249.',
            'muscle': 'Elbow (Posture 2)',
            'valid_range': '>0% MVC',
            'notes': 'Posture 2 - elbow task. N=7 subjects.'
        },
        'Rose et al. 2000 (Elbow)': {
            'citation': 'Rose, L., Ericsson, M., & Örtengren, R. (2000). Endurance time, pain and resumption in passive loading of the elbow joint. Ergonomics, 43, 405-420.',
            'muscle': 'Elbow',
            'valid_range': '0-100% MVC',
            'notes': 'Elbow passive loading. N=13 subjects.'
        },
        'Rose et al. 1992 (Elbow)': {
            'citation': 'Rose, L., Ericsson, M., Glimskär, B., Nordgren, B., & Örtengren, R. (1992). Ergo-Index: Development of a model to determine pause needs after fatigue and pain reactions during work. In Computer Applications in Ergonomics, Elsevier, pp. 461-468.',
            'muscle': 'Elbow joint',
            'valid_range': '0-100% MVC',
            'notes': 'Elbow joint specific. N=8 subjects.'
        },
        # Hand/Grip model
        'Manenica 1986 (Hand Grip)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'Hand/Grip (forearm flexors)',
            'valid_range': '0-100% MVC',
            'notes': 'Hand grip specific. N=18 subjects.'
        },
        # Back/Hip models
        'Manenica 1986 (Body Pull)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'Back/Hip (body pull task)',
            'valid_range': '0-100% MVC',
            'notes': 'Body pull task. N=18 subjects.'
        },
        'Manenica 1986 (Body Torque)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'Back/Hip (body torque task)',
            'valid_range': '0-100% MVC',
            'notes': 'Body torque task. N=18 subjects.'
        },
        'Manenica 1986 (Back)': {
            'citation': 'Manenica, I. (1986). A technique for postural load assessment. In: The Ergonomics of Working Postures, Taylor & Francis, pp. 270-277.',
            'muscle': 'Back muscles',
            'valid_range': '0-100% MVC',
            'notes': 'Back muscles specific. N=18 subjects.'
        },
        'Rohmert et al. 1986 (Back 1)': {
            'citation': 'Rohmert, W., Wangenheim, M., Mainzer, J., Zipp, P., & Lesser, W. (1986). A study stressing the need for a static postural force model for work analysis. Ergonomics, 29(10), 1235-1249.',
            'muscle': 'Back/Hip (Posture 3)',
            'valid_range': '>0% MVC',
            'notes': 'Posture 3 - back/hip task. N=7 subjects.'
        },
        'Rohmert et al. 1986 (Back 2)': {
            'citation': 'Rohmert, W., Wangenheim, M., Mainzer, J., Zipp, P., & Lesser, W. (1986). A study stressing the need for a static postural force model for work analysis. Ergonomics, 29(10), 1235-1249.',
            'muscle': 'Back/Hip (Posture 4)',
            'valid_range': '>0% MVC',
            'notes': 'Posture 4 - back/hip task. N=7 subjects.'
        },
        'Rohmert et al. 1986 (Back 3)': {
            'citation': 'Rohmert, W., Wangenheim, M., Mainzer, J., Zipp, P., & Lesser, W. (1986). A study stressing the need for a static postural force model for work analysis. Ergonomics, 29(10), 1235-1249.',
            'muscle': 'Back/Hip (Posture 5)',
            'valid_range': '>0% MVC',
            'notes': 'Posture 5 - back/hip task. N=7 subjects.'
        }
    }


def calculate_endurance_time(intensity, equation_func, output_unit='seconds'):
    """
    Calculate endurance time for a given intensity.
    """
    time_minutes = equation_func(intensity)
    
    if np.isnan(time_minutes) or time_minutes <= 0:
        return np.nan
    
    if output_unit == 'seconds':
        return time_minutes * 60
    return time_minutes


# ============================================================================
# SHARED SELECTOR STRUCTURE (mirrors SETT "Other ET-Intensity Models" tab)
# ============================================================================

ET_MODEL_CATEGORIES = {
    'General Models': [
        'Frey-Law & Avin 2010 (General)',
        'Rohmert 1960',
        'Monod & Scherrer 1965',
        'Huijgens 1981',
        'Sato et al. 1984 (General)',
        'Manenica 1986 (General)',
        'Sjogaard 1986',
        'Rose et al. 1992 (General)'
    ],
    'Shoulder Models': [
        'Frey-Law & Avin 2010 (Shoulder)',
        'Sato et al. 1984 (Shoulder)',
        'Rohmert et al. 1986 (Shoulder)',
        'Mathiassen & Ahsberg 1999 (Shoulder)',
        'Garg et al. 2002 (Shoulder)'
    ],
    'Elbow Models': [
        'Frey-Law & Avin 2010 (Elbow)',
        'Hagberg 1981 (Elbow)',
        'Manenica 1986 (Elbow)',
        'Sato et al. 1984 (Elbow)',
        'Rohmert et al. 1986 (Elbow)',
        'Rose et al. 2000 (Elbow)',
        'Rose et al. 1992 (Elbow)'
    ],
    'Hand/Grip Models': [
        'Frey-Law & Avin 2010 (Hand/Grip)',
        'Manenica 1986 (Hand Grip)'
    ],
    'Trunk/Back Models': [
        'Frey-Law & Avin 2010 (Trunk)',
        'Manenica 1986 (Body Pull)',
        'Manenica 1986 (Body Torque)',
        'Manenica 1986 (Back)',
        'Rohmert et al. 1986 (Back 1)',
        'Rohmert et al. 1986 (Back 2)',
        'Rohmert et al. 1986 (Back 3)'
    ],
    'Knee Models': [
        'Frey-Law & Avin 2010 (Knee)'
    ],
    'Ankle Models': [
        'Frey-Law & Avin 2010 (Ankle)'
    ]
}

DEFAULT_ET_REGION = 'General Models'
DEFAULT_ET_MODEL = 'Frey-Law & Avin 2010 (General)'

_ALL_EQUATIONS = None


def mht_seconds(fmvc, et_model_name):
    """Maximum holding time (s) at fMVC for the named ET model; NaN if undefined."""
    global _ALL_EQUATIONS
    if _ALL_EQUATIONS is None:
        _ALL_EQUATIONS = get_all_equations()
    return calculate_endurance_time(fmvc, _ALL_EQUATIONS[et_model_name], 'seconds')

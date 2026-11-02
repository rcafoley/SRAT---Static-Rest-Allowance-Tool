"""
ra_models.py - Rest allowance (RA) models for static muscular work.

Equations as compiled in El ahrache & Imbeau (2009), Table 1:
    RA (%) = resting time / holding time x 100
    fMVC   = %MVC / 100
    MHT    = maximum holding time (endurance time from an ET model)
    fMHT   = holding time / MHT

Rest time (s) = RA(%) / 100 x holding time (s).

MHT values come from the shared ET library (et_models.py), which returns
minutes; everything here is converted to SECONDS except where a model's
published form requires minutes (Rose et al. 1992 uses MHT in minutes).

Copyright Ryan C. A. Foley 2025
"""
from dataclasses import dataclass

import numpy as np

from et_models import mht_seconds

# ============================================================================
# CONSTANTS
# ============================================================================

INTENSITY_THRESHOLD_PCT = 15.0   # Rohmert 1973 / Bystrom: no fatigue below 15% MVC
MILNER_CONST = 4.61              # as published (ln(100) = 4.6052 -> 99% recovery)
MILNER_MIN_FMHT = 0.01           # 100 - 1/fMHT must be > 0  ->  fMHT > 0.01
FMHT_TOL = 1e-9                  # tolerance on the fMHT <= 1 domain boundary

ROHMERT_1973 = 'Rohmert 1973'
MILNER_1985 = 'Milner 1985'
ROSE_1992 = 'Rose et al. 1992'
BYSTROM_1994 = 'Byström & Fransson-Hall 1994'

RA_MODEL_ORDER = [ROHMERT_1973, MILNER_1985, ROSE_1992, BYSTROM_1994]

RA_COLORS = {
    ROHMERT_1973: '#003C71',
    MILNER_1985: '#E75D2A',
    ROSE_1992: '#6A994E',
    BYSTROM_1994: '#A23B72',
}


# ============================================================================
# RAW EQUATIONS (return RA in %, no domain checks)
# ============================================================================

def rohmert_1973_ra_pct(fmvc, fmht):
    """RA = 18 x fMHT^1.4 x (fMVC - 0.15)^0.5 x 100"""
    return 18.0 * (fmht ** 1.4) * ((fmvc - 0.15) ** 0.5) * 100.0


def milner_1985_ra_pct(fmht):
    """RA = 0.164 x [4.61 + ln(1 / (100 - fMHT^-1))]^-1 x 100  (99% recovery)"""
    inner = 100.0 - (1.0 / fmht)
    return 0.164 * (MILNER_CONST + np.log(1.0 / inner)) ** -1 * 100.0


def rose_1992_ra_pct(mht_min):
    """RA = 3 x MHT^-1.52 x 100, MHT in minutes"""
    return 3.0 * (mht_min ** -1.52) * 100.0


def bystrom_1994_ra_pct(pct_mvc):
    """RA = [(%MVC / 15) - 1] x 100"""
    return ((pct_mvc / 15.0) - 1.0) * 100.0


# ============================================================================
# MODEL METADATA
# ============================================================================

RA_MODEL_INFO = {
    ROHMERT_1973: {
        'uses_mht': True,
        'inputs': '%MVC, holding time, MHT (via fMHT)',
        'equation_text': 'RA = 18 × (fMHT)^1.4 × (fMVC − 0.15)^0.5 × 100',
        'equation_latex': r'RA = 18 \times f_{MHT}^{\,1.4} \times (f_{MVC} - 0.15)^{0.5} \times 100',
        'characteristics': [
            '%MVC and fMHT required',
            'No fatigue (RA = 0) when %MVC ≤ 15%',
            'Based on static work data for 13 muscle groups (upper limbs, trunk, lower limbs)',
        ],
        'domain': '15% < %MVC ≤ 100%, 0 < fMHT ≤ 1',
        'citation': 'Rohmert, W. (1973). Problems in determining rest allowances. Part 1: Use of modern '
                    'methods to evaluate stress and strain in static muscular work. Applied Ergonomics, 4(2), 91-95.',
    },
    MILNER_1985: {
        'uses_mht': True,
        'inputs': 'Holding time, MHT (via fMHT)',
        'equation_text': 'RA = 0.164 × [4.61 + ln(1 / (100 − fMHT⁻¹))]⁻¹ × 100',
        'equation_latex': r'RA = 0.164 \times \left[4.61 + \ln\!\left(\frac{1}{100 - f_{MHT}^{-1}}\right)\right]^{-1} \times 100',
        'characteristics': [
            '%MVC is not considered directly (enters only through MHT)',
            'fMHT required; MHT must be determined',
            'Posture without load applied on an external object',
            'RA corresponds to 99% recovery (El ahrache & Imbeau, 2009)',
        ],
        'domain': '0.01 < fMHT ≤ 1 (log argument undefined at fMHT ≤ 0.01)',
        'citation': 'Milner, N.P. (1985). Modelling fatigue and recovery in static postural exercise. '
                    'PhD thesis, University of Nottingham. RA form as given in El ahrache & Imbeau (2009).',
    },
    ROSE_1992: {
        'uses_mht': True,
        'inputs': 'MHT (minutes)',
        'equation_text': 'RA = 3 × MHT^−1.52 × 100   (MHT in minutes)',
        'equation_latex': r'RA = 3 \times MHT_{\,[min]}^{-1.52} \times 100',
        'characteristics': [
            'MHT required (minutes); holding time not considered in RA %',
            'Developed for construction work tasks',
            'No specific muscle group indicated',
        ],
        'domain': 'MHT > 0; holding time ≤ MHT',
        'citation': 'Rose, L., Ericsson, M., Glimskär, B., Nordgren, B., & Örtengren, R. (1992). Ergo-Index: '
                    'Development of a model to determine pause needs after fatigue and pain reactions during work. '
                    'In Computer Applications in Ergonomics, Occupational Safety and Health, Elsevier, pp. 461-468.',
    },
    BYSTROM_1994: {
        'uses_mht': False,
        'inputs': '%MVC',
        'equation_text': 'RA = [(%MVC / 15) − 1] × 100',
        'equation_latex': r'RA = \left[\frac{\%MVC}{15} - 1\right] \times 100',
        'characteristics': [
            '%MVC required; MHT not considered',
            'No fatigue (RA = 0) when %MVC ≤ 15%',
            'Intermittent work at the hand/wrist; short holding times',
        ],
        'domain': '15% < %MVC ≤ 100%',
        'citation': 'Byström, S. & Fransson-Hall, C. (1994). Acceptability of intermittent handgrip contractions '
                    'based on physiological response. Human Factors, 36(1), 158-171.',
    },
}

COMPILATION_CITATION = ('El ahrache, K. & Imbeau, D. (2009). Comparison of rest allowance models for static '
                        'muscular work. International Journal of Industrial Ergonomics, 39(1), 73-80.')


def model_uses_mht(model_name):
    return RA_MODEL_INFO[model_name]['uses_mht']


# ============================================================================
# CALCULATION WITH DOMAIN CHECKS
# ============================================================================

@dataclass
class RAResult:
    model: str
    pct_mvc: float
    holding_s: float
    et_model: str | None
    mht_s: float          # NaN when the RA model does not use MHT
    fmht: float           # NaN when the RA model does not use MHT
    ra_pct: float         # NaN when not computable
    rest_s: float         # NaN when not computable
    status: str           # ok | no_fatigue | infeasible | out_of_domain | et_undefined | invalid_input
    message: str = ''

    @property
    def ok(self):
        return self.status in ('ok', 'no_fatigue')

    @property
    def cycle_s(self):
        return self.holding_s + self.rest_s if self.ok else np.nan

    @property
    def duty_cycle(self):
        return self.holding_s / self.cycle_s if self.ok else np.nan


def compute_rest_allowance(model_name, pct_mvc, holding_s, et_model=None):
    """
    Rest allowance for one task.

    pct_mvc   : task intensity (% MVC, 0-100]
    holding_s : holding (task) duration in seconds
    et_model  : ET model name (from et_models) used for MHT; required when the RA model uses MHT
    """
    uses_mht = model_uses_mht(model_name)
    base = dict(model=model_name, pct_mvc=pct_mvc, holding_s=holding_s,
                et_model=et_model if uses_mht else None, mht_s=np.nan, fmht=np.nan)

    def result(ra_pct, status, message=''):
        rest = ra_pct / 100.0 * holding_s if np.isfinite(ra_pct) else np.nan
        return RAResult(**base, ra_pct=ra_pct, rest_s=rest, status=status, message=message)

    if not (0 < pct_mvc <= 100) or not (holding_s > 0):
        return result(np.nan, 'invalid_input', 'Intensity must be in (0, 100] %MVC and holding time > 0 s.')

    fmvc = pct_mvc / 100.0

    # --- MHT-based models -------------------------------------------------
    if uses_mht:
        if et_model is None:
            return result(np.nan, 'invalid_input', 'An ET model is required to determine MHT.')
        mht = mht_seconds(fmvc, et_model)
        # Rohmert 1973 defines RA = 0 at <=15% MVC regardless of MHT, so this
        # takes precedence over ET models that are undefined at low intensity.
        if model_name == ROHMERT_1973 and pct_mvc <= INTENSITY_THRESHOLD_PCT:
            if np.isfinite(mht) and mht > 0:
                base['mht_s'] = mht
                base['fmht'] = holding_s / mht
            return result(0.0, 'no_fatigue', 'Rohmert (1973) assumes no fatigue at ≤15% MVC (RA = 0).')
        if not np.isfinite(mht) or mht <= 0:
            return result(np.nan, 'et_undefined',
                          f'{et_model} is undefined at {pct_mvc:g}% MVC, so MHT cannot be determined.')
        base['mht_s'] = mht
        fmht = holding_s / mht
        base['fmht'] = fmht

        if fmht > 1 + FMHT_TOL:
            return result(np.nan, 'infeasible',
                          f'Holding time ({holding_s:.1f} s) exceeds MHT ({mht:.1f} s); fMHT = {fmht:.2f} > 1. '
                          f'The task cannot be sustained, so the model is outside its valid domain.')

        if model_name == ROHMERT_1973:
            if pct_mvc <= INTENSITY_THRESHOLD_PCT:
                return result(0.0, 'no_fatigue', 'Rohmert (1973) assumes no fatigue at ≤15% MVC (RA = 0).')
            return result(rohmert_1973_ra_pct(fmvc, fmht), 'ok')

        if model_name == MILNER_1985:
            if fmht <= MILNER_MIN_FMHT:
                return result(np.nan, 'out_of_domain',
                              f'Milner (1985) is undefined for fMHT ≤ {MILNER_MIN_FMHT} '
                              f'(here fMHT = {fmht:.4f}); 100 − 1/fMHT must be positive.')
            return result(milner_1985_ra_pct(fmht), 'ok')

        if model_name == ROSE_1992:
            return result(rose_1992_ra_pct(mht / 60.0), 'ok')

    # --- Intensity-only model ---------------------------------------------
    if model_name == BYSTROM_1994:
        if pct_mvc <= INTENSITY_THRESHOLD_PCT:
            return result(0.0, 'no_fatigue', 'Byström & Fransson-Hall (1994) assume no fatigue at ≤15% MVC (RA = 0).')
        return result(bystrom_1994_ra_pct(pct_mvc), 'ok')

    raise ValueError(f'Unknown RA model: {model_name}')


def rest_time_seconds(model_name, pct_mvc, holding_s, et_model=None):
    """Convenience wrapper for plotting: rest time (s) or NaN."""
    return compute_rest_allowance(model_name, pct_mvc, holding_s, et_model).rest_s

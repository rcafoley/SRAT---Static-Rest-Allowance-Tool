# SRAT - Static Rest Allowance Tool

Interactive web application for calculating rest allowances for static muscular work using prominent rest allowance (RA) models from the ergonomics literature, with maximum holding time (MHT) supplied by any of 31 endurance time (ET) models.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50+-red.svg)
![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)

## Purpose

This tool is intended to make rest allowance models quickly accessible for scientists, practitioners, and teachers interested in using these equations and learning about their differences. It is a companion to **SETT (Static Endurance Time Tool)** and shares its ET model library, so any ET model can be paired with any MHT-based rest allowance model.

## Features

- **4 Rest Allowance Models**: Rohmert (1973), Milner (1985), Rose et al. (1992), and Byström & Fransson-Hall (1994)
- **31 ET Models for MHT**: Frey-Law & Avin (2010) general and joint-specific models plus the El ahrache et al. (2006) compilation
- **Context-Aware Inputs**: The ET model selector is only active when the chosen RA model uses MHT
- **Rest Time in Seconds**: RA percentages are converted to absolute rest time and shown prominently
- **Interactive Visualization**: Rest time vs holding time, rest time vs intensity, work–rest cycles, and the ET curve supplying MHT
- **Model Comparison Page**: Side-by-side table, bar chart, and an intensity × holding time heatmap for any model
- **Domain Checking**: Inputs outside a model's valid range are flagged rather than returning misleading values

## Included Models

Equations as compiled in El ahrache & Imbeau (2009), Table 1.

| Model | Equation (RA %) | Inputs |
|-------|-----------------|--------|
| Rohmert (1973) | RA = 18 × fMHT^1.4 × (fMVC − 0.15)^0.5 × 100 | %MVC, holding time, MHT |
| Milner (1985) | RA = 0.164 × [4.61 + ln(1 / (100 − fMHT⁻¹))]⁻¹ × 100 | Holding time, MHT |
| Rose et al. (1992) | RA = 3 × MHT^−1.52 × 100 (MHT in minutes) | MHT |
| Byström & Fransson-Hall (1994) | RA = [(%MVC / 15) − 1] × 100 | %MVC |

Where:

- **RA (%)** = rest time ÷ holding time × 100
- **fMVC** = %MVC ÷ 100
- **MHT** = maximum holding time (endurance time from the selected ET model)
- **fMHT** = holding time ÷ MHT

The tool converts each result to an absolute rest time:

**Rest time (s) = RA ÷ 100 × holding time (s)**

### Domain Handling

| Condition | Behaviour |
|-----------|-----------|
| Holding time > MHT (fMHT > 1) | N/A for Rohmert, Milner, and Rose — the task cannot be sustained |
| ≤ 15% MVC | RA = 0 for Rohmert (1973) and Byström & Fransson-Hall (1994) (no fatigue assumed) |
| fMHT ≤ 0.01 | N/A for Milner (1985) — the log term is undefined |
| ET model undefined at the task intensity | N/A for MHT-based models (e.g., Rohmert 1960 below 15% MVC) |

## Quick Start

### Local Installation

```bash
# Clone this repository
git clone https://github.com/rcafoley/SRAT---Static-Rest-Allowance-Tool.git
cd SRAT---Static-Rest-Allowance-Tool

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit-rest-allowance-calculator.py
```

### Windows Quick Start

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit-rest-allowance-calculator.py
```

### Deploy to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "Create app"
4. Select your forked repository
5. Set main file path to `streamlit-rest-allowance-calculator.py`
6. Under Advanced settings, choose Python 3.10 or newer
7. Click "Deploy"

## Scientific Background

Rest allowance models estimate the recovery time needed after a static exertion so that fatigue does not accumulate across a work period. They are commonly expressed as a percentage of the holding time and depend on the intensity of the exertion (%MVC), the holding time relative to the maximum holding time (fMHT), or both.

Because several RA models depend on MHT, the choice of endurance time model directly affects the predicted rest. Pairing an RA model with a joint-specific ET model (e.g., Frey-Law & Avin, 2010) is a deliberate modelling choice, and comparing pairings helps show how sensitive a rest allowance is to that choice. El ahrache & Imbeau (2009) showed that these models can differ substantially for the same task.

### Applications

- Ergonomic workplace assessment
- Work–rest schedule design
- Comparing the sensitivity of rest allowance predictions to model choice
- Teaching fatigue and recovery concepts in ergonomics and kinesiology

### Limitations

- Models are based on **population averages**; individual recovery varies substantially
- Models were developed for **static (isometric) exertions**; dynamic and highly intermittent work may differ
- The Milner (1985) form is very sensitive near fMHT = 1 to the rounded constant 4.61 (vs. ln 100 = 4.605)
- Rose et al. (1992) does not consider holding time in RA %; rest time scales only through the RA × holding time conversion

## Project Structure

```
SRAT---Static-Rest-Allowance-Tool/
├── streamlit-rest-allowance-calculator.py  # Main Streamlit application
├── ra_models.py                            # Rest allowance equations and domain checks
├── et_models.py                            # Shared ET model library (from SETT)
├── requirements.txt                        # Python dependencies
└── README.md                               # This file
```

## Author

**Ryan C. A. Foley**  
PhD Candidate, CSEP Clinical Exercise Physiologist  
Occupational Neuromechanics and Ergonomics (ONE) Laboratory  
Ontario Tech University

- GitHub: [@rcafoley](https://github.com/rcafoley)
- Website: [rcafoley.github.io](https://rcafoley.github.io)
- Email: ryan.foley@ontariotechu.ca

## Key References

**Model Compilation:**

El ahrache, K. & Imbeau, D. (2009). Comparison of rest allowance models for static muscular work. *International Journal of Industrial Ergonomics*, 39(1), 73-80.

**Rest Allowance Models:**

Rohmert, W. (1973). Problems in determining rest allowances. Part 1: Use of modern methods to evaluate stress and strain in static muscular work. *Applied Ergonomics*, 4(2), 91-95.

Milner, N.P. (1985). *Modelling fatigue and recovery in static postural exercise*. PhD thesis, University of Nottingham.

Rose, L., Ericsson, M., Glimskär, B., Nordgren, B., & Örtengren, R. (1992). Ergo-Index: Development of a model to determine pause needs after fatigue and pain reactions during work. In *Computer Applications in Ergonomics, Occupational Safety and Health*, Elsevier, pp. 461-468.

Byström, S. & Fransson-Hall, C. (1994). Acceptability of intermittent handgrip contractions based on physiological response. *Human Factors*, 36(1), 158-171.

**Endurance Time:**

Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis investigation. *Ergonomics*, 53(1), 109-129.

El ahrache, K., Imbeau, D., & Farbos, B. (2006). Percentile values for determining maximum endurance times for static muscular work. *International Journal of Industrial Ergonomics*, 36, 99-108.

---
*© 2025 ONE Laboratory, Ontario Tech University*

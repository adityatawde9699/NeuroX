# NeuroX dataset acquisition

This directory is reserved for approved, de-identified datasets used for research prototypes. Do not commit raw participant data, clinical records, audio, or derived identifying information.

## Recommended acquisition order

1. **LASI / LASI-DAD** — India-focused ageing, cognition, health, and dementia data. Request access through the [IIPS LASI portal](https://www.iipsindia.ac.in/content/LASI-data) and [LASI-DAD](https://www.lasi-dad.org/data/overview).
2. **ADNI** — longitudinal clinical, cognitive, imaging, and biomarker data. Register and follow the [ADNI data-access process](https://adni.loni.usc.edu/data-samples/adni-data/).
3. **OASIS** — open ageing and neuroimaging cohorts subject to the dataset licence. See [OASIS](https://www.oasis-brains.org/).
4. **DementiaBank** — consented dementia speech data with controlled access. See the [Pitt corpus access page](https://talkbank.org/dementia/access/English/Pitt.html).
5. **Global ageing cohorts** — HRS, ELSA, SHARE, CHARLS, KLoSA, JSTAR, TILDA, MHAS, CRELES, MARS, ELSI-Brazil, and HAALSI through the [Gateway to Global Aging Data](https://g2aging.org/).

## Local layout

Keep downloaded files outside version control:

```text
data/
  raw/          # original downloads; never commit
  processed/    # de-identified, documented extracts; never commit
  derived/      # model-ready features; never commit
  register.csv  # dataset name, licence, approval, provenance, checksum
```

Before modelling, record the licence, consent/IRB constraints, permitted use, provenance, checksum, preprocessing steps, and train/validation/test split. Models must be framed as supportive research prototypes, not diagnostic or treatment tools.

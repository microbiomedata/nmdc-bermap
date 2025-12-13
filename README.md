<a href="https://github.com/dalito/linkml-project-copier"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-teal.json" alt="Copier Badge" style="max-width:100%;"/></a>

# The NMDC BER Map

__STATUS__: Experimental, AI-generated, some information may be incomplete or incorrect.

A LinkML schema and knowledge base for DOE BER (Biological and Environmental Research) funded research programs, including:

- **Bioenergy Research Centers (BRCs)**: GLBRC, JBEI, CABBI, CBI
- **Genomic Science SFAs**: ENIGMA, m-CAFEs, Microbes Persist, PMI, SEED, and more
- **Environmental System Science SFAs**: Watershed Function, River Corridor, Mercury SFA, WaDE, and more
- **User Facilities**: JGI, EMSL, KBase, ESS-DIVE, NMDC

The schema captures metadata about studies, datasets, publications, key findings, KBase analyses, and NMDC integration priorities.

## Key Features

- **Schema-driven**: LinkML schema with Python datamodel generation
- **Reference validation**: Validates that publication excerpts appear in cited papers using [linkml-reference-validator](https://github.com/linkml/linkml-reference-validator)
- **NMDC integration**: Tracks NMDC study IDs and ingest priorities for microbiome studies
- **BRC API integration**: Scripts to fetch and sync datasets from the BRC API (api.bioenergy.org)
- **OWL export**: Converts knowledge base to OWL for semantic queries

## Quick Start

```bash
# Install dependencies
just install

# Validate the database
just validate-db

# Validate publication references
just validate-refs

# Fetch BRC datasets from API
just fetch-brc-datasets
```

## Repository Structure

* [db/](db/) - Knowledge base data
  * [sfas-brcs.yaml](db/sfas-brcs.yaml) - Main database of programs, studies, datasets, publications
  * [brc_datasets/](db/brc_datasets/) - Individual dataset files from BRC API (by center)
* [src/nmdc_sfas_brcs/](src/nmdc_sfas_brcs/)
  * [schema/](src/nmdc_sfas_brcs/schema) - LinkML schema (authoritative source)
  * [datamodel/](src/nmdc_sfas_brcs/datamodel) - Generated Python classes
  * [scripts/](src/nmdc_sfas_brcs/scripts) - Data fetching and processing scripts
  * [validators/](src/nmdc_sfas_brcs/validators) - Custom validation tools
* [project/](project/) - Generated artifacts (OWL, JSON Schema, etc.)
* [docs/](docs/) - Documentation

## Common Commands

```bash
just validate-db          # Validate database against schema
just validate-refs        # Validate publication excerpts
just validate-enums       # Validate enum ontology mappings
just fetch-brc-datasets   # Fetch all BRC datasets from API
just gen-abox-tbox        # Generate OWL representation
just gen-python           # Regenerate Python datamodels
```

## Related Resources

- [NMDC](https://microbiomedata.org/) - National Microbiome Data Collaborative
- [BRC API](https://api.bioenergy.org/) - Bioenergy Research Centers dataset API
- [KBase](https://www.kbase.us/) - DOE Systems Biology Knowledgebase
- [ESS-DIVE](https://ess-dive.lbl.gov/) - Environmental System Science Data Infrastructure

## Credits

This project uses the template [linkml-project-copier](https://github.com/dalito/linkml-project-copier) published as [doi:10.5281/zenodo.15163584](https://doi.org/10.5281/zenodo.15163584).

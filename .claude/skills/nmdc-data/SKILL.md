---
name: nmdc-data
description: Skills for querying microbiome data in NMDC. Use this proactively for anything related to microbes and microbiomes. Use for anything involving NMDC IDs (e.g. prefixed `nmdc:`)
---

# Command line tool

These tools require `nmdc` on the command line.

Use `nmdc --help` or `nmdc COMMAND --help` for more detailed info, the most common operations are shown here.

Most tools allow export to CSV, by appending options:

`nmdc COMMAND MAIN_OPTS  -f csv -o out.csv`

## Looking up and searching biosamples

Lookup by id:

`nmdc biosample --id nmdc:bsm-11-NNNNNN`

Finding samples for a study study:

`nmdc biosample --filter 'associated_studies: nmdc:sty-11-NNNNNN'`

Searching in a bounding box:

`nmdc biosample --bbox "30,-120,40,-100"`

Search by GOLD classification:

`nmdc biosample --filter 'ecosystem: Engineered'`


If your starting point is a different kind of object, use `link` to navigate.

## Studies

Fetch a study by ID:

`nmdc study --id nmdc:sty-11-34xj1150`

Search by ecosystem:

`nmdc study --filter 'ecosystem_category: Aquatic' --limit 5`

## Finding linked objects

The NMDC data model at a high level is:

 * Study -> Biosample -> DataObject

You can traverse objects up and down and across multiple hops using `link`

Example:

`nmdc link nmdc:dobj-11-m71bzv60`

Filtering by object type:

`nmdc link nmdc:dobj-11-m71bzv60 -t nmdc:Biosample`

Note that the `link` command will also include workflow objects but these typically don't need to be referenced individually

## Finding data for a study, sample, or data object

If you have a data object ID, then you can fetch its metadata:

`nmdc data-object --id nmdc:dobj-11-m71bzv60`

The JSON will include a URL. Download this the usual way

## Dumping data for a study

If you need to dump multiple files for analysis, use `dump-study`

Example:

`nmdc dump-study nmdc:sty-11-aygzgv51 ./my_data --download-data -t "Kraken2 Taxonomic Classification, Functional Annotation GFF"`

This creates a structure, with the study at the top, and all data organized under a folder for each sample:

```
my_data/
  study.json -- metadata about nmdc:sty-11-aygzgv51
  nmdc_bsm-11-FIRST-SAMPLE
    biosample.json -- metadata about the first sample
    data_objects/
      nmdc_wfgan-11-NNNNNN_functional_annotation.gff -- genes with functional ann in col9. can be analyzed using GFF skill
      nmdc_wfrbt-11-NNNNNN_kraken2_classification.tsv -- taxonomic classification.
```



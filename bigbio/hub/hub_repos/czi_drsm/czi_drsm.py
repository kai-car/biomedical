# coding=utf-8
# Copyright 2022 The HuggingFace Datasets Authors and Gully Burns.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Full documentation on writing dataset loading scripts can be found here:
https://huggingface.co/docs/datasets/dataset_script

To create a dataset loading script you will create a class and implement 3 methods:
  * `_info`: Establishes the schema for the dataset, and returns a datasets.DatasetInfo object.
  * `_split_generators`: Downloads and extracts data for each split (e.g. train/val/test) or associate local data with each split.
  * `_generate_examples`: Creates examples from data on disk that conform to each schema defined in `_info`.

TODO: Before submitting your script, delete this doc string and replace it with a description of your dataset.

[bigbio_schema_name] = (kb, pairs, qa, text, t2t, entailment)
"""

import os
from typing import List, Tuple, Dict

import datasets
import pandas as pd
from pathlib import Path

import bigbio.utils.parsing as parse
from bigbio.utils import schemas
from bigbio.utils.configs import BigBioConfig
from bigbio.utils.constants import Lang, Tasks
from bigbio.utils.license import Licenses

#from .bigbiohub import BigBioConfig
#from .bigbiohub import Tasks

#from .bigbiohub import 

_LOCAL = False

_CITATION = """\
@article{,
  author    = {},
  title     = {},
  journal   = {},
  volume    = {},
  year      = {},
  url       = {},
  doi       = {},
  biburl    = {},
  bibsource = {}
}
"""

_DATASETNAME = "czi_drsm"

_DESCRIPTION = """\
Research article document classification dataset based on aspects of disease research. Currently, the dataset consists of three subsets: 
(A) classifies title/abstracts of papers into most popular subtypes of clinical, basic, and translational papers (~20k papers); 
(B) identifies whether a title/abstract of a paper describes substantive research into Quality of Life (~10k papers); 
(C) identifies if a paper is a natural history study (~10k papers). 
These classifications are particularly relevant in rare disease research, a field that is generally understudied.
"""

_HOMEPAGE = "https://github.com/chanzuckerberg/DRSM-corpus/"
_LICENSE = "CC0 1.0"

_LANGUAGES = ['English']
_PUBMED = False
_LOCAL = False

# For publicly available datasets you will most likely end up passing these URLs to dl_manager in _split_generators.
# In most cases the URLs will be the same for the source and bigbio config.
# However, if you need to access different files for each config you can have multiple entries in this dict.
# This can be an arbitrarily nested dict/list of URLs (see below in `_split_generators` method)
_URLS = {
    'base': "https://raw.githubusercontent.com/chanzuckerberg/DRSM-corpus/main/v1/drsm_corpus_v1.tsv",
    'qol': "https://raw.githubusercontent.com/chanzuckerberg/DRSM-corpus/main/v2/qol_all_2022_12_15.tsv",
    'nhs': "https://raw.githubusercontent.com/chanzuckerberg/DRSM-corpus/main/v2/nhs_all_2023_03_31.tsv"
}

_SUPPORTED_TASKS = [Tasks.TEXT_CLASSIFICATION]  

_SOURCE_VERSION = "1.0.0"
_BIGBIO_VERSION = "1.0.0"

_CLASS_NAMES_BASE = [
    "clinical characteristics or disease pathology",
    "therapeutics in the clinic",
    "disease mechanism",
    "patient-based therapeutics",
    "other",
    "irrelevant"
    ]

_CLASS_NAMES_QOL = [
    "-1 - the paper is not a primary experimental study in rare disease",
    "0 - the study does not directly investigate quality of life",
    "1 - the study investigates qol but not as its primary contribution",
    "2 - the study's primary contribution centers on quality of life measures"
    ]

_CLASS_NAMES_NHS = [
    "-1 - the paper is not a primary experimental study in rare disease",
    "0 - the study is not directly investigating the natural history of a disease",
    "1 - the study includes some elements a natural history but not as its primary contribution",
    "2 - the study's primary contribution centers on observing the time course of a rare disease"
    ]

class DRSMBaseDataset(datasets.GeneratorBasedBuilder):
    """DRSM Document Classification Datasets."""

    SOURCE_VERSION = datasets.Version(_SOURCE_VERSION)
    BIGBIO_VERSION = datasets.Version(_BIGBIO_VERSION)

    # You will be able to load the "source" or "bigbio" configurations with
    #ds_source = datasets.load_dataset('drsm_source_dataset', name='source')
    #ds_bigbio = datasets.load_dataset('drsm_bigbio_dataset', name='bigbio')

    # For local datasets you can make use of the `data_dir` and `data_files` kwargs
    # https://huggingface.co/docs/datasets/add_dataset.html#downloading-data-files-and-organizing-splits
    # ds_source = datasets.load_dataset('my_dataset', name='source', data_dir="/path/to/data/files")
    # ds_bigbio = datasets.load_dataset('my_dataset', name='bigbio', data_dir="/path/to/data/files")

    # TODO: For each dataset, implement Config for Source and BigBio;
    #  If dataset contains more than one subset (see examples/bioasq.py) implement for EACH of them.
    #  Each of them should contain:
    #   - name: should be unique for each dataset config eg. bioasq10b_(source|bigbio)_[bigbio_schema_name]
    #   - version: option = (SOURCE_VERSION|BIGBIO_VERSION)
    #   - description: one line description for the dataset
    #   - schema: options = (source|bigbio_[bigbio_schema_name])
    #   - subset_id: subset id is the canonical name for the dataset (eg. bioasq10b)
    #  where [bigbio_schema_name] = ()

    BUILDER_CONFIGS = [
        BigBioConfig(
            name="czi_drsm_base_source",
            version=SOURCE_VERSION,
            description="czi_drsm base source schema",
            schema="base_source",
            subset_id="czi_drsm_base",
        ),
        BigBioConfig(
            name="czi_drsm_bigbio_base_text",
            version=BIGBIO_VERSION,
            description="czi_drsm base BigBio schema",
            schema="bigbio_text",
            subset_id="czi_drsm_base",
        ),
        BigBioConfig(
            name="czi_drsm_qol_source",
            version=SOURCE_VERSION,
            description="czi_drsm source schema for Quality of Life studies",
            schema="qol_source",
            subset_id="czi_drsm_qol",
        ),
        BigBioConfig(
            name="czi_drsm_bigbio_qol_text",
            version=BIGBIO_VERSION,
            description="czi_drsm BigBio schema for Quality of Life studies",
            schema="bigbio_text",
            subset_id="czi_drsm_qol",
        ),
        BigBioConfig(
            name="czi_drsm_nhs_source",
            version=SOURCE_VERSION,
            description="czi_drsm source schema for Natural History Studies",
            schema="nhs_source",
            subset_id="czi_drsm_nhs",
        ),
        BigBioConfig(
            name="czi_drsm_bigbio_nhs_text",
            version=BIGBIO_VERSION,
            description="czi_drsm BigBio schema for Natural History Studies",
            schema="bigbio_text",
            subset_id="czi_drsm_nhs",
        ),
    ]

    DEFAULT_CONFIG_NAME = "czi_drsm_bigbio_base_text"

    def _info(self) -> datasets.DatasetInfo:

        # Create the source schema; this schema will keep all keys/information/labels as close to the original dataset as possible.

        # You can arbitrarily nest lists and dictionaries.
        # For iterables, use lists over tuples or `datasets.Sequence`

        if self.config.schema == "base_source":
            features = datasets.Features(
                {
                    "document_id": datasets.Value("string"),
                    "labeling_state": datasets.Value("string"),
                    "explanation": datasets.Value("string"),
                    "correct_label": [datasets.ClassLabel(names=_CLASS_NAMES_BASE)],
                    "agreement": [datasets.Value("string")],
                    "title": [datasets.Value("string")],
                    "abstract": [datasets.Value("string")],
                }
            )

        elif self.config.schema == "qol_source":
            features = datasets.Features(
                {
                    "document_id": datasets.Value("string"),
                    "labeling_state": datasets.Value("string"),
                    "correct_label": [datasets.ClassLabel(names=_CLASS_NAMES_QOL)],
                    "explanation": datasets.Value("string"),
                    "agreement": [datasets.Value("string")],
                    "title": [datasets.Value("string")],
                    "abstract": [datasets.Value("string")]
                }
            )

        elif self.config.schema == "nhs_source":
            features = datasets.Features(
                {
                    "document_id": datasets.Value("string"),
                    "labeling_state": datasets.Value("string"),
                    "correct_label": [datasets.ClassLabel(names=_CLASS_NAMES_NHS)],
                    "explanation": datasets.Value("string"),
                    "agreement": [datasets.Value("string")],
                    "title": [datasets.Value("string")],
                    "abstract": [datasets.Value("string")],
                }
            )

        # For example bigbio_kb, bigbio_t2t
        elif self.config.schema == "bigbio_text":
            features = schemas.text_features

        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=features,
            homepage=_HOMEPAGE,
            license=_LICENSE,
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager) -> List[datasets.SplitGenerator]:
        """Returns SplitGenerators."""

        if 'base' in self.config.name:
            url = _URLS['base']
        elif 'qol' in self.config.name:
            url = _URLS['qol']
        elif 'nhs' in self.config.name:
            url = _URLS['nhs']
        else:
            raise ValueError("Invalid config name: {}".format(self.config.name))        

        data_file = dl_manager.download_and_extract(url)
        df = pd.read_csv(data_file, sep="\t", encoding="utf-8").fillna('')

        # load tsv file into huggingface dataset
        ds = datasets.Dataset.from_pandas(df)
        
        # generate train_test split
        ds_dict = ds.train_test_split(test_size=0.2, seed=42)
        ds_dict2 = ds_dict['test'].train_test_split(test_size=0.5, seed=42)
        
        # dump train, val, test to disk
        data_dir = Path(data_file).parent
        ds_dict['train'].to_csv(data_dir / "train.tsv", sep="\t", index=False)
        ds_dict2['train'].to_csv(data_dir / "validation.tsv", sep="\t", index=False)
        ds_dict2['test'].to_csv(data_dir / "test.tsv", sep="\t", index=False)    

        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                gen_kwargs={
                    "filepath": data_dir / "train.tsv",
                    "split": "train",
                },
            ),
            datasets.SplitGenerator(
                name=datasets.Split.VALIDATION,
                gen_kwargs={
                    "filepath": data_dir / "validation.tsv",
                    "split": "validation",
                },
            ),
            datasets.SplitGenerator(
                name=datasets.Split.TEST,
                gen_kwargs={
                    "filepath": data_dir / "test.tsv",
                    "split": "test",
                },
            )
        ]

    # method parameters are unpacked from `gen_kwargs` as given in `_split_generators`
    def _generate_examples(self, filepath, split) -> Tuple[int, Dict]:
        """Yields examples as (key, example) tuples."""
        df = pd.read_csv(filepath, sep="\t", encoding="utf-8").fillna('')
        print(len(df))
        for id_, l in df.iterrows():
            if self.config.subset_id == "czi_drsm_base":
                doc_id = l[0]
                labeling_state = l[1]
                correct_label = l[2]
                agreement = l[3]
                explanation = l[4]
                title = l[5]
                abstract = l[6]
            elif self.config.subset_id == "czi_drsm_qol":
                doc_id = l[0]
                labeling_state = l[1]
                correct_label = l[2][1:-1]
                explanation = l[3]
                agreement = l[4]
                title = l[5]
                abstract = l[6]                
            elif self.config.subset_id == "czi_drsm_nhs":
                doc_id = l[0]
                labeling_state = l[1]
                correct_label = l[2][1:-1]
                explanation = ''
                agreement = l[3]
                title = l[4]
                abstract = l[5]

            if "_source" in self.config.schema:
                yield id_, {
                    "document_id": doc_id,  
                    "labeling_state": labeling_state,
                    "explanation": explanation,
                    "correct_label": [correct_label],
                    "agreement": str(agreement),
                    "title": title,
                    "abstract": abstract
                }
            elif self.config.schema == "bigbio_text":                    
                yield id_, {
                    "id": id_,
                    "document_id": doc_id,
                    "text": title + " " + abstract,
                    "labels": [correct_label]
                }

# This template is based on the following template from the datasets package:
# https://github.com/huggingface/datasets/blob/master/templates/new_dataset_script.py

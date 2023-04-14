# @Copyright: CEA-LIST/DIASI/SIALV/LVA (2023)
# @Author: CEA-LIST/DIASI/SIALV/LVA <pixano@cea.fr>
# @License: CECILL-C
#
# This software is a collaborative computer program whose purpose is to
# generate and explore labeled data for computer vision applications.
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software. You can use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
#
# http://www.cecill.info

import time
from pathlib import Path

import pyarrow as pa
import pyarrow.dataset as arrow_ds
import pyarrow.parquet as pq
import pydantic


class DatasetInfo(pydantic.BaseModel):
    id: str
    name: str
    description: str
    num_elements: int
    preview: str | None


class Dataset:
    """Dataset class

    Args:
        _path (Path): Dataset path
        _info (DatasetInfo): Dataset info
        _table (pa.Table): Dataset table
    """

    def __init__(self, path: Path):
        self._path = path
        self._info = DatasetInfo.parse_file(self._path / "spec.json")
        self._table = None

    @property
    def info(self):
        return self._info

    @property
    def media_path(self):
        return self._path / "media"

    @property
    def table(self):
        if self._table is None:
            st = time.process_time()
            self._table = pq.read_table(self._path / "db", use_legacy_dataset=False)
            et = time.process_time()
            res = et - st
            print("CPU Execution time:", res, "seconds")

        return self._table

    def load(self):
        partitioning = arrow_ds.partitioning(
            pa.schema([("split", pa.string())]), flavor="hive"
        )
        return arrow_ds.dataset(self._path / "db", partitioning=partitioning)


class InferenceDataset(Dataset):
    """Inference Dataset

    Args:
        _path (Path): Dataset path
        _info (DatasetInfo): Dataset info
        _table (pa.Table): Dataset table
    """

    def __init__(self, path: Path):
        self._path = path
        self._info = DatasetInfo.parse_file(self._path / "infer.json")
        self._table = None

    def load(self):
        partitioning = arrow_ds.partitioning(
            pa.schema([("split", pa.string())]), flavor="hive"
        )
        return arrow_ds.dataset(
            self._path,
            partitioning=partitioning,
            ignore_prefixes=["info"],
            exclude_invalid_files=True,
        )
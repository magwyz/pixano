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

from abc import ABC, abstractmethod
from pathlib import Path


class Exporter(ABC):
    """Abstract Data Exmporter class"""

    @abstractmethod
    def export_dataset(self, input_dir: Path, export_dir: Path):
        """Export dataset back to original format

        Args:
            input_dir (Path): Input directory
            export_dir (Path): Export directory
        """

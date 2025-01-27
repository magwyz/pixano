# @Copyright: CEA-LIST/DIASI/SIALV/LVA (2023)
# @Author: CEA-LIST/DIASI/SIALV/LVA <pixano@cea.fr>
# @License: CECILL-C
#
# This software is a collaborative computer program whose purpose is to
# generate and explore labeled data for computer vision applications.
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software. You can use,
# modify and/ or redistribute the software under the terms of the CeCILL-C
# license as circulated by CEA, CNRS and INRIA at the following URL
#
# http://www.cecill.info

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from pixano_inference import transformers

from pixano.apps import create_app
from pixano.data import COCOImporter, DatasetInfo, DatasetItem, DatasetStat, Settings


class AppTestCase(unittest.TestCase):
    def setUp(self):
        # Create temporary directory
        self.temp_dir = Path.cwd() / "library"
        self.temp_dir.mkdir(exist_ok=False)

        # Create a COCO dataset
        import_dir = self.temp_dir / "coco"
        input_dirs = {
            "image": Path("tests/assets/coco_dataset/image"),
            "objects": Path("tests/assets/coco_dataset"),
        }
        importer = COCOImporter(
            name="coco",
            description="COCO dataset",
            input_dirs=input_dirs,
            splits=["val"],
        )
        dataset = importer.import_dataset(import_dir, copy=True)

        # Set dataset ID
        dataset.info.id = "coco_dataset"
        dataset.save_info()

        # Create dataset stats
        stats = [
            DatasetStat(
                name="Some numerical statistics",
                type="numerical",
                histogram=[
                    {"bin_start": 0.0, "bin_end": 1.0, "counts": 2, "split": "train"},
                    {"bin_start": 1.0, "bin_end": 2.0, "counts": 4, "split": "train"},
                    {"bin_start": 2.0, "bin_end": 3.0, "counts": 6, "split": "train"},
                    {"bin_start": 3.0, "bin_end": 4.0, "counts": 8, "split": "train"},
                ],
                range=[0.0, 10.0],
            ),
            DatasetStat(
                name="Some categorical statistics",
                type="categorical",
                histogram=[
                    {"Some categorical statistics": "a", "counts": 2, "split": "train"},
                    {"Some categorical statistics": "b", "counts": 4, "split": "train"},
                    {"Some categorical statistics": "c", "counts": 6, "split": "train"},
                    {"Some categorical statistics": "d", "counts": 8, "split": "train"},
                ],
            ),
        ]
        with open(import_dir / "stats.json", "w", encoding="utf-8") as f:
            json.dump([stat.model_dump() for stat in stats], f)

        # Launch app
        self.client = TestClient(create_app(Settings()))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_get_datasets(self):
        response = self.client.get("/datasets")
        output = response.json()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(output), 1)

        for ds in output:
            ds_info = DatasetInfo.model_validate(ds)
            self.assertIsInstance(ds_info, DatasetInfo)

    def test_get_dataset(self):
        response = self.client.get("/datasets/coco_dataset")
        output = response.json()

        self.assertEqual(response.status_code, 200)

        ds_info = DatasetInfo.model_validate(output)
        self.assertIsInstance(ds_info, DatasetInfo)

    def test_get_dataset_items(self):
        response = self.client.get("/datasets/coco_dataset/items")
        output = response.json()

        self.assertEqual(response.status_code, 200)

        self.assertIn("items", output)
        self.assertIn("total", output)
        self.assertIn("page", output)
        self.assertIn("size", output)
        self.assertIn("pages", output)

        self.assertEqual(len(output["items"]), 3)

        for item in output["items"]:
            ds_item = DatasetItem.model_validate(item)
            self.assertIsInstance(ds_item, DatasetItem)

    def test_search_dataset_items(self):
        # Without embeddings
        response = self.client.post(
            "/datasets/coco_dataset/search",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"model": "CLIP", "search": "bear"},
        )

        self.assertEqual(response.status_code, 404)

        # With embeddings
        model = transformers.CLIP()
        model.process_dataset(
            dataset_dir=self.temp_dir / "coco",
            process_type="search_emb",
            views=["image"],
        )

        response = self.client.post(
            "/datasets/coco_dataset/search",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"model": "CLIP", "search": "bear"},
        )
        output = response.json()

        self.assertEqual(response.status_code, 200)

        self.assertIn("items", output)
        self.assertIn("total", output)
        self.assertIn("page", output)
        self.assertIn("size", output)
        self.assertIn("pages", output)

        self.assertEqual(len(output["items"]), 3)

        for item in output["items"]:
            ds_item = DatasetItem.model_validate(item)
            self.assertIsInstance(ds_item, DatasetItem)

    def test_get_dataset_item(self):
        response = self.client.get("/datasets/coco_dataset/items/139")
        output = response.json()

        self.assertEqual(response.status_code, 200)

        ds_item = DatasetItem.model_validate(output)
        self.assertIsInstance(ds_item, DatasetItem)

    def test_post_dataset_item(self):
        response_1 = self.client.get("/datasets/coco_dataset/items/139")
        output = response_1.json()

        ds_item = DatasetItem.model_validate(output)

        response_2 = self.client.post(
            "/datasets/coco_dataset/items/127",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=ds_item.model_dump(),
        )

        self.assertEqual(response_2.status_code, 200)

    def test_get_dataset_item_embeddings(self):
        response = self.client.get("/datasets/coco_dataset/items/139/embeddings/SAM")

        # TODO: Can't test embeddings without model weights
        self.assertEqual(response.status_code, 404)

    def test_get_models(self):
        with tempfile.NamedTemporaryFile(dir=self.temp_dir / "models", suffix=".onnx"):
            response = self.client.get("/models")
            output = response.json()

            self.assertEqual(response.status_code, 200)

            self.assertEqual(len(output), 1)

            for model in output:
                self.assertIsInstance(model, str)
                self.assertIn(".onnx", model)

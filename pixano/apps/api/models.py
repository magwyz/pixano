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

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from pixano.data import Settings

router = APIRouter(tags=["models"])


@lru_cache
def get_settings():
    """Get app settings

    Returns:
        Settings: App settings
    """

    return Settings()


@router.get("/models", response_model=list[str])
async def get_models() -> list[str]:
    """Load models

    Returns:
        list[str]: List of models
    """

    # Load list of models
    models = []
    for model_path in get_settings().data_dir.glob("models/*.onnx"):
        models.append(model_path.name)

    # Return list of models
    if models:
        return models
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No models found in {get_settings().data_dir.absolute()}",
        )

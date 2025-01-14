<script lang="ts">
  /**
   * @copyright CEA
   * @author CEA
   * @license CECILL
   *
   * This software is a collaborative computer program whose purpose is to
   * generate and explore labeled data for computer vision applications.
   * This software is governed by the CeCILL-C license under French law and
   * abiding by the rules of distribution of free software. You can use,
   * modify and/ or redistribute the software under the terms of the CeCILL-C
   * license as circulated by CEA, CNRS and INRIA at the following URL
   *
   * http://www.cecill.info
   */

  // Imports
  import * as ort from "onnxruntime-web";

  import { afterUpdate, createEventDispatcher, onMount } from "svelte";

  import {
    AnnotationToolbar,
    Canvas2D,
    CategoryToolbar,
    LabelPanel,
    tools,
  } from "@pixano/canvas2d";
  import { api, ConfirmModal, utils, LoadingModal, SelectModal, WarningModal } from "@pixano/core";
  import { SAM, npy } from "@pixano/models";

  import { interactiveSegmenterModel } from "./stores";

  import type {
    BBox,
    DatasetCategory,
    DatasetInfo,
    DatasetItem,
    ItemLabels,
    Label,
    Mask,
  } from "@pixano/core";

  import type { InteractiveImageSegmenter, InteractiveImageSegmenterOutput } from "@pixano/models";

  // Exports
  export let selectedDataset: DatasetInfo;
  export let selectedItem: DatasetItem;
  export let annotations: ItemLabels;
  export let classes: Array<DatasetCategory>;
  export let masks: Array<Mask>;
  export let bboxes: Array<BBox>;
  export let currentPage: number;
  export let models: Array<string>;
  export let saveFlag: boolean;
  export let activeLearningFlag: boolean;

  const dispatch = createEventDispatcher();

  // Modals
  let loadingModelModal = false;
  let categoryNameModal = false;
  let selectItemModal = false;
  let embeddingsErrorModal = false;

  // Category colors
  let colorMode = "category";
  let colorScale = handleLabelColors();

  // Filters
  let maskOpacity = 1.0;
  let bboxOpacity = 0.0;
  let confidenceThreshold = 0.0;

  // Current annotations
  let currentAnn: InteractiveImageSegmenterOutput = null;
  let currentAnnCatName = "";
  const currentAnnSource = "Pixano Annotator";

  // Models
  let embeddings: Record<string, ort.Tensor> = {};
  let selectedModelName: string;
  let modelLoaded = false;
  const sam = new SAM();

  // Tools
  const tools_lists: Array<Array<tools.Tool>> = [];
  const imageTools: Array<tools.Tool> = [];
  const classificationTools: Array<tools.Tool> = [];
  const annotationTools: Array<tools.Tool> = [];
  const pointSelectionTool = tools.createPointSelectionTool();
  const rectangleTool = tools.createRectangleTool();
  const deleteTool = tools.createDeleteTool();
  const panTool = tools.createPanTool();
  const classifTool = tools.createClassifTool();
  annotationTools.push(pointSelectionTool);
  annotationTools.push(rectangleTool);
  annotationTools.push(deleteTool);
  classificationTools.push(classifTool);
  imageTools.push(panTool);
  tools_lists.push(imageTools);
  tools_lists.push(classificationTools);
  tools_lists.push(annotationTools);
  let selectedTool: tools.Tool = panTool;

  function until(condition: () => boolean): Promise<void> {
    return new Promise<void>((resolve) => {
      let i = setInterval(() => {
        console.log("AnnotationWorkspace.until - Waiting for user confirmation");
        if (condition()) {
          resolve();
          clearInterval(i);
        }
      }, 500);
    });
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter") handleAddCurrentAnn();
  }

  async function loadModel() {
    loadingModelModal = true;
    console.log("AnnotationWorkspace.loadModel");
    await sam.init("/data/models/" + selectedModelName);
    interactiveSegmenterModel.set(sam);
    interactiveSegmenterModel.subscribe((segmenter) => {
      if (segmenter) {
        pointSelectionTool.modes.plus.postProcessor = segmenter as InteractiveImageSegmenter;
        pointSelectionTool.modes.minus.postProcessor = segmenter as InteractiveImageSegmenter;
        rectangleTool.postProcessor = segmenter as InteractiveImageSegmenter;
      }
    });
    // Embeddings
    const start = Date.now();
    const item = await api.getItemEmbeddings(
      selectedDataset.id,
      selectedItem.id,
      selectedModelName,
    );
    console.log(
      "AnnotationWorkspace.loadModel - api.getItemEmbeddings in",
      Date.now() - start,
      "ms",
    );
    if (item) {
      for (const [viewId, viewEmbeddingBytes] of Object.entries(item.embeddings)) {
        try {
          const viewEmbeddingArray = npy.parse(npy.b64ToBuffer(viewEmbeddingBytes.data));
          embeddings[viewId] = new ort.Tensor(
            "float32",
            viewEmbeddingArray.data,
            viewEmbeddingArray.shape,
          );
        } catch (e) {
          console.log("AnnotationWorkspace.loadModel - Error loading embeddings", e);
        }
      }
      modelLoaded = true;
    } else {
      embeddingsErrorModal = true;
      selectedModelName = "";
      selectedTool = panTool;
    }
    loadingModelModal = false;
  }

  function handleAddCurrentFeatures() {
    console.log("AnnotationWorkspace.handleAddCurrentFeatures");
    if (currentAnnCatName !== "") {
      addCurrentFeatures();
      dispatch("enableSaveFlag");
    }
  }

  function addCurrentFeatures() {
    if ("label" in selectedItem.features) {
      // TODO get label from "editables"(? - to define)
      selectedItem.features.label.value = currentAnnCatName;
      // Update visibility
      selectedItem = selectedItem;
    } else {
      selectedItem.features.label = {
        name: "label",
        dtype: "text",
        value: currentAnnCatName,
      };
    }
  }

  function handleAddCurrentAnn() {
    console.log("AnnotationWorkspace.handleAddCurrentAnn");
    if (currentAnn) {
      // Check if category name provided
      if (currentAnnCatName === "") {
        categoryNameModal = true;
      } else {
        addCurrentAnn();
        dispatch("enableSaveFlag");
      }
    }
  }

  function addCurrentAnn() {
    // Add the new label's category to the class list if it doesn't already exist.
    let currentAnnCatId: number;

    if (!classes.some((c) => c.name === currentAnnCatName)) {
      if (classes.length > 0) {
        currentAnnCatId = Math.max(...classes.map((o) => o.id)) + 1;
      } else {
        currentAnnCatId = 1;
      }
      classes.push({ id: currentAnnCatId, name: currentAnnCatName });
    } else {
      currentAnnCatId = classes.find((obj) => obj.name === currentAnnCatName).id;
    }

    // Add current mask
    const currentMask = <Mask>{
      id: currentAnn.id,
      viewId: currentAnn.viewId,
      svg: currentAnn.output.masksImageSVG,
      rle: currentAnn.output.rle,
      catId: currentAnnCatId,
      visible: true,
      opacity: 1.0,
    };
    masks.push(currentMask);

    // Check if the new label's view already exists in the current annotations
    if (!annotations[currentAnnSource]) {
      annotations[currentAnnSource] = {
        id: currentAnnSource,
        views: {},
        numLabels: 0,
        opened: true,
        visible: true,
      };
    }

    // Check if the new label's view already exists in the current annotations
    if (!annotations[currentAnnSource].views[currentAnn.viewId]) {
      annotations[currentAnnSource].views[currentAnn.viewId] = {
        id: currentAnn.viewId,
        categories: {},
        numLabels: 0,
        opened: true,
        visible: true,
      };
    }

    // Check if the new label's category already exists in the current annotations
    if (!annotations[currentAnnSource].views[currentAnn.viewId].categories[currentAnnCatId]) {
      annotations[currentAnnSource].views[currentAnn.viewId].categories[currentAnnCatId] = {
        labels: {},
        id: currentAnnCatId,
        name: currentAnnCatName,
        opened: true,
        visible: true,
      };
    }

    const currentLabel = <Label>{
      id: currentAnn.id,
      categoryId: currentAnnCatId,
      categoryName: currentAnnCatName,
      sourceId: currentAnnSource,
      viewId: currentAnn.viewId,
      maskOpacity: 1.0,
      bboxOpacity: 1.0,
      visible: true,
    };
    annotations[currentAnnSource].views[currentAnn.viewId].categories[currentAnnCatId].labels[
      currentAnn.id
    ] = currentLabel;

    annotations[currentAnnSource].numLabels += 1;
    annotations[currentAnnSource].views[currentAnn.viewId].numLabels += 1;

    // Validate current annotation
    currentAnn.validated = true;

    // Update visibility
    masks = masks;
    annotations = annotations;
  }

  async function handleChangeSelectedItem(itemId: string) {
    console.log("AnnotationWorkspace.handleChangeSelectedItem");
    if (itemId !== selectedItem.id) {
      if (!saveFlag) {
        changeSelectedItem(itemId);
      } else {
        selectItemModal = true;
        await until(() => selectItemModal == false);
        if (!saveFlag) {
          changeSelectedItem(itemId);
        }
      }
    }
  }

  function changeSelectedItem(itemId: string) {
    currentAnnCatName = "";
    dispatch("selectItem", itemId);
  }

  function handleDeleteLabel(label: Label) {
    console.log("AnnotationWorkspace.handleDeleteLabel");

    // Remove from annotations
    delete annotations[label.sourceId].views[label.viewId].categories[label.categoryId].labels[
      label.id
    ];
    annotations[label.sourceId].numLabels -= 1;
    annotations[label.sourceId].views[label.viewId].numLabels -= 1;

    // Remove from masks / bboxes
    masks = masks.filter((mask) => mask.id !== label.id);
    bboxes = bboxes.filter((bbox) => bbox.id !== label.id);

    dispatch("enableSaveFlag");

    // Update visibility
    annotations = annotations;
  }

  function handleLabelVisibility(label: Label) {
    // Try and find a mask
    const mask = masks.find((mask) => mask.id === label.id && mask.viewId === label.viewId);
    if (mask) {
      mask.visible = label.visible;
      mask.opacity = label.maskOpacity;
    }

    // Try and find a bbox
    const bbox = bboxes.find((bbox) => bbox.id === label.id && bbox.viewId === label.viewId);
    if (bbox) {
      bbox.visible = label.visible;
      bbox.opacity = label.bboxOpacity;
    }

    // Update visibility
    masks = masks;
    bboxes = bboxes;
  }

  function handleLabelFilters() {
    for (const source of Object.values(annotations)) {
      for (const view of Object.values(source.views)) {
        for (const category of Object.values(view.categories)) {
          for (const label of Object.values(category.labels)) {
            // Opacity filters
            label.maskOpacity = maskOpacity;
            label.bboxOpacity = bboxOpacity;
            // Confidence threshold filter
            if (label.confidence) {
              label.visible =
                label.confidence >= confidenceThreshold &&
                category.visible &&
                view.visible &&
                source.visible;
            }
            handleLabelVisibility(label);
          }
        }
      }
    }
  }

  function handleLabelColors() {
    let range: Array<number>;
    if (colorMode === "category") {
      range = [
        Math.min(...classes.map((cat) => cat.id)),
        Math.max(...classes.map((cat) => cat.id)),
      ];
    } else if (colorMode === "source") {
      range = [0, Object.keys(annotations).length];
    }
    return utils.ordinalColorScale(range.map((i) => i.toString())) as (id: string) => string;
  }

  function handleLoadNextPage() {
    dispatch("loadNextPage");
  }

  onMount(async () => {
    if (annotations) {
      console.log("AnnotationWorkspace.onMount");
      colorScale = handleLabelColors();
    }
    // If only one SAM model, load as default
    if (models.length > 0) {
      let samModels = models.filter((m) => m.includes("sam"));
      if (samModels.length == 1) {
        selectedModelName = samModels[0];
        await loadModel();
      }
    }
  });

  afterUpdate(() => {
    console.log("AnnotationWorkspace.afterUpdate");
    annotations = annotations;
    classes = classes;
    masks = masks;
    bboxes = bboxes;
    handleLabelFilters();
  });
</script>

<div class="flex h-full w-full pt-20 bg-slate-100">
  {#if selectedItem}
    <Canvas2D
      {selectedItem}
      bind:selectedTool
      {colorScale}
      {masks}
      {bboxes}
      {embeddings}
      bind:currentAnn
    />
    <AnnotationToolbar {tools_lists} bind:selectedTool />
    {#if annotations}
      <LabelPanel
        {selectedItem}
        {annotations}
        {colorScale}
        bind:maskOpacity
        bind:bboxOpacity
        bind:confidenceThreshold
        {selectedDataset}
        {currentPage}
        bind:activeLearningFlag
        on:labelVisibility={(event) => handleLabelVisibility(event.detail)}
        on:labelFilters={handleLabelFilters}
        on:deleteLabel={(event) => handleDeleteLabel(event.detail)}
        on:selectItem={(event) => handleChangeSelectedItem(event.detail)}
        on:loadNextPage={handleLoadNextPage}
      />
    {/if}
    {#if selectedTool && selectedTool.type == tools.ToolType.Classification}
      <!-- TODO WIP -->
      <CategoryToolbar
        bind:currentAnnCatName
        bind:classes
        bind:selectedTool
        {pointSelectionTool}
        {colorScale}
        placeholder="Label name"
        on:addCurrentAnn={handleAddCurrentFeatures}
      />
    {:else if selectedTool && (selectedTool.type == tools.ToolType.PointSelection || selectedTool.type == tools.ToolType.Rectangle)}
      {#if !modelLoaded}
        {#if models.length > 0}
          <SelectModal
            message="Please select your model for interactive segmentation."
            choices={models}
            ifNoChoices={""}
            bind:selected={selectedModelName}
            on:confirm={loadModel}
          />
        {:else}
          <WarningModal
            message="It looks like there is no model for interactive segmentation in youre dataset library."
            details="Please refer to our interactive annotation notebook for information on how to export your model to ONNX."
            on:confirm={() => {
              selectedTool = panTool;
            }}
          />{/if}
      {/if}
      <CategoryToolbar
        bind:currentAnnCatName
        bind:classes
        bind:selectedTool
        {pointSelectionTool}
        {colorScale}
        on:addCurrentAnn={handleAddCurrentAnn}
      />
    {/if}
    {#if categoryNameModal}
      <WarningModal
        message="Please set a category name to save your annotation."
        on:confirm={() => (categoryNameModal = false)}
      />
    {/if}
    {#if selectItemModal}
      <ConfirmModal
        message="You have unsaved changes."
        confirm="Continue without saving"
        on:confirm={() => ((saveFlag = false), (selectItemModal = false))}
        on:cancel={() => (selectItemModal = !selectItemModal)}
      />
    {/if}
    {#if embeddingsErrorModal}
      <WarningModal
        message="No embeddings found for model {selectedModelName}."
        details="Please refer to our interactive annotation notebook for information on how to compute embeddings on your dataset."
        on:confirm={() => (embeddingsErrorModal = false)}
      />
    {/if}
    {#if loadingModelModal}
      <LoadingModal />
    {/if}
  {/if}
</div>

<!-- Pixano Annotator footer -->
<div
  class="absolute bottom-0 right-0 px-2 py-1 text-sm border-t border-l rounded-tl-lg
  text-slate-500 bg-slate-50 border-slate-300"
>
  Pixano Annotator
</div>

<svelte:window on:keydown={handleKeyDown} />

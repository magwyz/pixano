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
  import { createEventDispatcher, onMount } from "svelte";

  import { api, Dashboard, LoadingModal, WarningModal } from "@pixano/core";

  import { Table } from "@pixano/table";

  import type { DatasetInfo, DatasetItems } from "@pixano/core";
  import {
    svg_clear,
    svg_filter,
    svg_first_page,
    svg_grid,
    svg_last_page,
    svg_list,
    svg_next_page,
    svg_prev_page,
    svg_search,
  } from "@pixano/core/src/icons";

  // Exports
  export let selectedDataset: DatasetInfo;
  export let selectedTab: string;
  export let currentPage: number;

  // Semantic search
  let search: string = "";
  let selectedSearchModel: string;
  const searchModels: Array<string> = [];
  if ("embeddings" in selectedDataset.tables) {
    for (const table of selectedDataset.tables.embeddings) {
      if (table.type == "search") {
        // Initialize selected search model
        if (!selectedSearchModel) {
          selectedSearchModel = table.source;
        }
        searchModels.push(table.source);
      }
    }
  }

  // Page navigation
  const itemsPerPage = 100;

  // Modals
  let loadingResultsModal = false;
  let datasetErrorModal = false;

  const dispatch = createEventDispatcher();

  function handleSelectItem(itemId: string) {
    dispatch("selectItem", itemId);

    selectedTab = "";
  }

  async function loadPage() {
    let res: DatasetItems;
    let query = { model: selectedSearchModel, search: search };

    // Load page
    const start = Date.now();
    if (search == "") {
      // Standard page
      res = await api.getDatasetItems(selectedDataset.id, currentPage, itemsPerPage);
      console.log("DatasetExplorer.loadPage - api.getDatasetItems in", Date.now() - start, "ms");
    } else {
      // Search page
      loadingResultsModal = true;
      res = await api.searchDatasetItems(selectedDataset.id, query, currentPage, itemsPerPage);
      console.log("DatasetExplorer.loadPage - api.searchDatasetItems in", Date.now() - start, "ms");
    }

    // Results
    loadingResultsModal = false;
    if (res == null) {
      datasetErrorModal = true;
    } else {
      selectedDataset.page = res;
    }
  }

  async function handleClearSearch() {
    (document.getElementById("sem-search-input") as HTMLInputElement).value = "";
    await handleSearch();
  }

  async function handleGoToFirstPage() {
    if (currentPage > 1) {
      currentPage = 1;
      await loadPage();
    }
  }

  async function handleGoToPreviousPage() {
    if (currentPage > 1) {
      currentPage -= 1;
      await loadPage();
    }
  }

  async function handleGoToNextPage() {
    if (selectedDataset.page.total > currentPage * itemsPerPage) {
      currentPage += 1;
      await loadPage();
    }
  }

  async function handleGoToLastPage() {
    if (selectedDataset.page.total > currentPage * itemsPerPage) {
      currentPage = Math.ceil(selectedDataset.page.total / itemsPerPage);
      await loadPage();
    }
  }

  async function handleSearch() {
    search = (document.getElementById("sem-search-input") as HTMLInputElement).value;
    currentPage = 1;
    await loadPage();
  }

  onMount(async () => {
    search = "";
    await loadPage();
  });
</script>

<div class="w-full h-full p-20 flex flex-col bg-slate-100 text-slate-800">
  {#if selectedDataset.page}
    <!-- Items list -->
    <div class="w-full h-full flex flex-col">
      {#if selectedTab === "database"}
        <div class="py-5 h-20 flex space-x-2 items-center">
          <button>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_list} fill="currentcolor" />
            </svg>
          </button>
          <button>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_grid} fill="currentcolor" />
            </svg>
          </button>
          <button>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_filter} fill="currentcolor" />
            </svg>
          </button>
          <div class="flex-grow" />
          <div class="relative flex items-center">
            {#if searchModels.length > 0}
              <select class="h-10 px-4 mx-4 border rounded bg-slate-50 border-slate-300">
                {#each searchModels as model}
                  <option value={selectedSearchModel}>
                    {model}
                  </option>
                {/each}
              </select>

              <div class="relative flex items-center">
                <input
                  id="sem-search-input"
                  type="text"
                  value={search}
                  placeholder="Semantic search using {selectedSearchModel}"
                  class="h-10 pl-10 pr-4 rounded-full border text-slate-800 placeholder-slate-500 bg-slate-50 border-slate-300 shadow-slate-300 accent-main"
                  on:change={handleSearch}
                />
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  height="48"
                  viewBox="0 -960 960 960"
                  width="48"
                  class="absolute left-2 h-5 w-5 text-slate-500 pointer-events-none"
                >
                  <path d={svg_search} fill="currentcolor" />
                </svg>
                {#if search !== ""}
                  <button
                    class="absolute right-2 p-1 rounded-full transition-colors hover:bg-slate-300"
                    on:click={handleClearSearch}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      height="48"
                      viewBox="0 -960 960 960"
                      width="48"
                      class="h-5 w-5 text-slate-500"
                    >
                      <path d={svg_clear} fill="currentcolor" />
                    </svg>
                  </button>
                {/if}
              </div>
            {/if}
          </div>
        </div>
        <Table
          items={selectedDataset.page.items}
          on:selectItem={(event) => handleSelectItem(event.detail)}
        />
      {:else if selectedTab === "dashboard"}
        <div class="py-5 h-20 flex space-x-2 items-center" />
        <Dashboard {selectedDataset} />
      {/if}
    </div>

    <!-- Page navigation -->
    {#if selectedTab === "database"}
      <div class="w-full py-5 h-20 flex justify-center items-center text-slate-800">
        {#if selectedDataset.page.total > itemsPerPage}
          <button on:click={handleGoToFirstPage}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_first_page} fill="currentcolor" />
            </svg>
          </button>

          <button on:click={handleGoToPreviousPage}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_prev_page} fill="currentcolor" />
            </svg>
          </button>
        {/if}

        <span class="mx-4">
          {1 + itemsPerPage * (currentPage - 1)} - {Math.min(
            itemsPerPage * currentPage,
            selectedDataset.page.total,
          )} of
          {selectedDataset.page.total}
        </span>

        {#if selectedDataset.page.total > itemsPerPage}
          <button on:click={handleGoToNextPage}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_next_page} fill="currentcolor" />
            </svg>
          </button>

          <button on:click={handleGoToLastPage}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              height="48"
              viewBox="0 -960 960 960"
              width="48"
              class="h-8 w-8 p-1 rounded-full transition-colors hover:bg-slate-300"
            >
              <path d={svg_last_page} fill="currentcolor" />
            </svg>
          </button>
        {/if}
      </div>
    {/if}
    {#if datasetErrorModal}
      <WarningModal
        message="Error while retrieving dataset items."
        details="Please look at the application logs for more information, and report this issue if the error persists."
        on:confirm={() => (datasetErrorModal = false)}
      />
    {/if}
    {#if loadingResultsModal}
      <LoadingModal />
    {/if}
  {/if}
</div>

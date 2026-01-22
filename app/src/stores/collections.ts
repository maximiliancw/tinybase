/**
 * Collections Pinia Store
 *
 * Manages collections and records state.
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api';
import type { CollectionResponse, RecordResponse } from '@/client';

export const useCollectionsStore = defineStore('collections', () => {
  // State
  const collections = ref<CollectionResponse[]>([]);
  const currentCollection = ref<CollectionResponse | null>(null);
  const records = ref<RecordResponse[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Actions
  async function fetchCollections(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.listCollections();
      collections.value = response.data as CollectionResponse[];
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch collections';
    } finally {
      loading.value = false;
    }
  }

  async function fetchCollection(name: string): Promise<CollectionResponse | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.getCollection({
        path: { collection_name: name },
      });
      currentCollection.value = response.data as CollectionResponse;
      return response.data as CollectionResponse;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch collection';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function createCollection(data: {
    name: string;
    label: string;
    schema: any;
    options?: any;
  }): Promise<CollectionResponse | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.createCollection({
        body: data,
      });
      await fetchCollections();
      return response.data as CollectionResponse;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create collection';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function deleteCollection(name: string): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      await api.collections.deleteCollection({
        path: { collection_name: name },
      });
      await fetchCollections();
      return true;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete collection';
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRecords(
    collectionName: string,
    limit = 100,
    offset = 0
  ): Promise<{ records: RecordResponse[]; total: number }> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.listRecords({
        path: { collection_name: collectionName },
        query: { limit, offset },
      });
      records.value = response.data.records as RecordResponse[];
      return response.data as { records: RecordResponse[]; total: number };
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch records';
      return { records: [], total: 0 };
    } finally {
      loading.value = false;
    }
  }

  async function createRecord(
    collectionName: string,
    data: Record<string, any>
  ): Promise<RecordResponse | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.createRecord({
        path: { collection_name: collectionName },
        body: { data },
      });
      return response.data as RecordResponse;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create record';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRecord(
    collectionName: string,
    recordId: string
  ): Promise<RecordResponse | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.getRecord({
        path: { collection_name: collectionName, record_id: recordId },
      });
      return response.data as RecordResponse;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch record';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateRecord(
    collectionName: string,
    recordId: string,
    data: Record<string, any>
  ): Promise<RecordResponse | null> {
    loading.value = true;
    error.value = null;

    try {
      const response = await api.collections.updateRecord({
        path: { collection_name: collectionName, record_id: recordId },
        body: { data },
      });
      return response.data as RecordResponse;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to update record';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function deleteRecord(collectionName: string, recordId: string): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      await api.collections.deleteRecord({
        path: { collection_name: collectionName, record_id: recordId },
      });
      return true;
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete record';
      return false;
    } finally {
      loading.value = false;
    }
  }

  return {
    // State
    collections,
    currentCollection,
    records,
    loading,
    error,
    // Actions
    fetchCollections,
    fetchCollection,
    createCollection,
    deleteCollection,
    fetchRecords,
    createRecord,
    fetchRecord,
    updateRecord,
    deleteRecord,
  };
});

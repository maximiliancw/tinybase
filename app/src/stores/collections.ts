/**
 * Collections Pinia Store
 * 
 * Manages collections and records state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { 
  api, 
  type CollectionResponse as Collection,
  type RecordResponse as Record 
} from '../api'

// Re-export types for convenience
export type { Collection, Record }

export const useCollectionsStore = defineStore('collections', () => {
  // State
  const collections = ref<Collection[]>([])
  const currentCollection = ref<Collection | null>(null)
  const records = ref<Record[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchCollections(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await api.collections.listCollections()
      collections.value = response.data as Collection[]
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch collections'
    } finally {
      loading.value = false
    }
  }

  async function fetchCollection(name: string): Promise<Collection | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.collections.getCollection({
        path: { collection_name: name },
      })
      currentCollection.value = response.data as Collection
      return response.data as Collection
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch collection'
      return null
    } finally {
      loading.value = false
    }
  }

  async function createCollection(data: {
    name: string
    label: string
    schema: any
    options?: any
  }): Promise<Collection | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.collections.createCollection({
        body: data,
      })
      await fetchCollections()
      return response.data as Collection
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create collection'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteCollection(name: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.collections.deleteCollection({
        path: { collection_name: name },
      })
      await fetchCollections()
      return true
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete collection'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchRecords(
    collectionName: string,
    limit = 100,
    offset = 0
  ): Promise<{ records: Record[]; total: number }> {
    loading.value = true
    error.value = null

    try {
      const response = await api.collections.listRecords({
        path: { collection_name: collectionName },
        query: { limit, offset },
      })
      records.value = response.data.records as Record[]
      return response.data as { records: Record[]; total: number }
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to fetch records'
      return { records: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  async function createRecord(
    collectionName: string,
    data: Record<string, any>
  ): Promise<Record | null> {
    loading.value = true
    error.value = null

    try {
      const response = await api.collections.createRecord({
        path: { collection_name: collectionName },
        body: { data },
      })
      return response.data as Record
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to create record'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteRecord(
    collectionName: string,
    recordId: string
  ): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      await api.collections.deleteRecord({
        path: { collection_name: collectionName, record_id: recordId },
      })
      return true
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to delete record'
      return false
    } finally {
      loading.value = false
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
    deleteRecord,
  }
})

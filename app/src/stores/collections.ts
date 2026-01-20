/**
 * Collections Pinia Store
 * 
 * Manages collections and records state.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listCollectionsApiCollectionsGet,
  getCollectionApiCollectionsCollectionNameGet,
  createCollectionApiCollectionsPost,
  deleteCollectionApiCollectionsCollectionNameDelete,
  listRecordsApiCollectionsCollectionNameRecordsGet,
  createRecordApiCollectionsCollectionNameRecordsPost,
  deleteRecordApiCollectionsCollectionNameRecordsRecordIdDelete,
  type Collection as ApiCollection,
  type RecordResponse,
} from '../api'

export interface Collection {
  id: string
  name: string
  label: string
  schema: {
    fields: Array<{
      name: string
      type: string
      required: boolean
      default?: any
      min_length?: number
      max_length?: number
      min?: number
      max?: number
      description?: string
    }>
  }
  options: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Record {
  id: string
  collection_id: string
  owner_id: string | null
  data: Record<string, any>
  created_at: string
  updated_at: string
}

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
      const response = await listCollectionsApiCollectionsGet()
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
      const response = await getCollectionApiCollectionsCollectionNameGet({
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
      const response = await createCollectionApiCollectionsPost({
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
      await deleteCollectionApiCollectionsCollectionNameDelete({
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
      const response = await listRecordsApiCollectionsCollectionNameRecordsGet({
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
      const response = await createRecordApiCollectionsCollectionNameRecordsPost({
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
      await deleteRecordApiCollectionsCollectionNameRecordsRecordIdDelete({
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

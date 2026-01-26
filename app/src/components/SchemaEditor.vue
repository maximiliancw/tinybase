<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useToast } from '../composables/useToast';
import { useCollectionsStore } from '../stores/collections';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import Icon from './Icon.vue';

interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  unique?: boolean;
  description?: string;
  default?: any;
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
  collection?: string;
}

interface Schema {
  fields: SchemaField[];
}

interface Props {
  modelValue: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const toast = useToast();
const collectionsStore = useCollectionsStore();
const editorMode = ref<'json' | 'visual'>('visual');
const jsonText = ref(props.modelValue);
const jsonError = ref('');
const visualFields = ref<SchemaField[]>([]);
const fieldErrors = ref<Record<number, string>>({});

// Fetch collections for reference dropdown
onMounted(async () => {
  if (collectionsStore.collections.length === 0) {
    await collectionsStore.fetchCollections();
  }
});

// Parse JSON to visual fields
function parseJsonToVisual() {
  try {
    const schema: Schema = JSON.parse(jsonText.value);
    if (schema.fields && Array.isArray(schema.fields)) {
      visualFields.value = schema.fields.map((field) => ({
        name: field.name || '',
        type: field.type || 'string',
        required: field.required ?? false,
        unique: field.unique ?? false,
        description: field.description || '',
        default: field.default,
        min: field.min,
        max: field.max,
        min_length: field.min_length,
        max_length: field.max_length,
        pattern: field.pattern || '',
        collection: field.collection || '',
      }));
      jsonError.value = '';
    } else {
      throw new Error('Invalid schema: missing fields array');
    }
  } catch (err: any) {
    jsonError.value = err.message;
    // Initialize with empty field if JSON is invalid
    if (visualFields.value.length === 0) {
      visualFields.value = [
        {
          name: '',
          type: 'string',
          required: false,
        },
      ];
    }
  }
}

// Parse visual fields to JSON - only include non-empty/relevant properties
function parseVisualToJson() {
  const cleanedFields: SchemaField[] = visualFields.value
    .filter((f) => f.name.trim() !== '')
    .map((f) => {
      const field: SchemaField = {
        name: f.name,
        type: f.type,
        required: f.required,
      };

      // Only include properties that are set
      if (f.unique) field.unique = f.unique;
      if (f.description?.trim()) field.description = f.description;
      if (f.default !== undefined && f.default !== null && f.default !== '') {
        field.default = f.default;
      }

      // Type-specific properties
      if (f.type === 'number' || f.type === 'integer' || f.type === 'float') {
        if (f.min !== undefined && f.min !== null) field.min = Number(f.min);
        if (f.max !== undefined && f.max !== null) field.max = Number(f.max);
      }

      if (f.type === 'string') {
        if (f.min_length !== undefined && f.min_length !== null) {
          field.min_length = Number(f.min_length);
        }
        if (f.max_length !== undefined && f.max_length !== null) {
          field.max_length = Number(f.max_length);
        }
        if (f.pattern?.trim()) field.pattern = f.pattern;
      }

      if (f.type === 'reference' && f.collection?.trim()) {
        field.collection = f.collection;
      }

      return field;
    });

  const schema: Schema = { fields: cleanedFields };
  jsonText.value = JSON.stringify(schema, null, 2);
  jsonError.value = '';
}

// Initialize visual fields from JSON
parseJsonToVisual();

// Watch for external changes
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== jsonText.value) {
      jsonText.value = newValue;
      parseJsonToVisual();
    }
  }
);

// Validate and emit JSON
function validateAndEmit() {
  try {
    JSON.parse(jsonText.value);
    jsonError.value = '';
    emit('update:modelValue', jsonText.value);
  } catch (err: any) {
    jsonError.value = `JSON Error: ${err.message}`;
  }
}

// Format JSON
function formatJson() {
  try {
    const parsed = JSON.parse(jsonText.value);
    jsonText.value = JSON.stringify(parsed, null, 2);
    jsonError.value = '';
    emit('update:modelValue', jsonText.value);
    toast.success('JSON formatted successfully');
  } catch (err: any) {
    jsonError.value = `JSON Error: ${err.message}`;
    toast.error('Invalid JSON - cannot format');
  }
}

// Watch JSON text changes
watch(jsonText, () => {
  validateAndEmit();
});

// Switch to JSON mode
function switchToJson() {
  parseVisualToJson();
  editorMode.value = 'json';
  emit('update:modelValue', jsonText.value);
}

// Switch to visual mode
function switchToVisual() {
  parseJsonToVisual();
  editorMode.value = 'visual';
}

// Add new field
function addField() {
  visualFields.value.push({
    name: '',
    type: 'string',
    required: false,
  });
}

// Remove field
function removeField(index: number) {
  visualFields.value.splice(index, 1);
  if (visualFields.value.length === 0) {
    addField();
  }
  parseVisualToJson();
  emit('update:modelValue', jsonText.value);
}

// Validate field name
function validateFieldName(name: string, index: number): string {
  if (!name.trim()) {
    return 'Field name is required';
  }

  // Check snake_case
  const snakeCaseRegex = /^[a-z][a-z0-9_]*$/;
  if (!snakeCaseRegex.test(name)) {
    return 'Field name must be snake_case (lowercase letters, numbers, underscores only)';
  }

  // Check for uniqueness
  const duplicates = visualFields.value.filter(
    (f, i) => i !== index && f.name.toLowerCase() === name.toLowerCase()
  );
  if (duplicates.length > 0) {
    return 'Field name must be unique';
  }

  return '';
}

// Update field and sync to JSON
function updateField() {
  // Validate all fields
  fieldErrors.value = {};
  visualFields.value.forEach((field, i) => {
    if (field.name.trim()) {
      const error = validateFieldName(field.name, i);
      if (error) {
        fieldErrors.value[i] = error;
      }
    }
  });

  parseVisualToJson();
  emit('update:modelValue', jsonText.value);
}

// Handle type change - clear type-specific properties
function onTypeChange(field: SchemaField) {
  // Clear properties not valid for new type
  if (field.type !== 'string') {
    field.min_length = undefined;
    field.max_length = undefined;
    field.pattern = '';
  }
  if (field.type !== 'number' && field.type !== 'integer' && field.type !== 'float') {
    field.min = undefined;
    field.max = undefined;
  }
  if (field.type !== 'reference') {
    field.collection = '';
  }
  // Can't have unique on complex types
  if (field.type === 'object' || field.type === 'array') {
    field.unique = false;
  }
  updateField();
}

// Field types
const fieldTypes = ['string', 'number', 'boolean', 'object', 'array', 'date', 'reference'];

// Check if field type supports unique
function supportsUnique(type: string): boolean {
  return !['object', 'array'].includes(type);
}

// Check if field type is numeric
function isNumericType(type: string): boolean {
  return ['number', 'integer', 'float'].includes(type);
}

const isValid = computed(() => jsonError.value === '');
</script>

<template>
  <div class="space-y-4">
    <Tabs
      :model-value="editorMode"
      @update:model-value="(v) => (v === 'json' ? switchToJson() : switchToVisual())"
    >
      <TabsList class="grid w-full grid-cols-2">
        <TabsTrigger value="visual"> Visual Mode </TabsTrigger>
        <TabsTrigger value="json"> JSON Mode </TabsTrigger>
      </TabsList>

      <!-- JSON Mode -->
      <TabsContent value="json" class="space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Badge :variant="isValid ? 'success' : 'destructive'">
              {{ isValid ? 'Valid' : 'Invalid' }}
            </Badge>
            <p v-if="jsonError" class="text-xs text-destructive">{{ jsonError }}</p>
          </div>
          <Button variant="outline" size="sm" @click="formatJson">
            <Icon name="Code" :size="14" class="mr-1" />
            Format
          </Button>
        </div>
        <Textarea
          v-model="jsonText"
          :rows="12"
          class="font-mono text-sm"
          placeholder='{"fields": [{"name": "title", "type": "string", "required": true}]}'
        />
      </TabsContent>

      <!-- Visual Mode -->
      <TabsContent value="visual" class="space-y-4">
        <div class="max-h-[400px] overflow-y-auto space-y-3 pr-2">
          <Card v-for="(field, index) in visualFields" :key="index" class="p-4">
            <CardContent class="p-0">
              <div class="space-y-3">
                <!-- Name and Type Row -->
                <div class="flex items-start justify-between gap-2">
                  <div class="flex-1 grid gap-3 sm:grid-cols-2">
                    <div class="space-y-2">
                      <Label :for="`field-name-${index}`">Field Name</Label>
                      <Input
                        :id="`field-name-${index}`"
                        v-model="field.name"
                        placeholder="e.g., title"
                        :class="{ 'border-destructive': fieldErrors[index] }"
                        @input="updateField"
                      />
                      <p v-if="fieldErrors[index]" class="text-xs text-destructive">
                        {{ fieldErrors[index] }}
                      </p>
                    </div>
                    <div class="space-y-2">
                      <Label :for="`field-type-${index}`">Type</Label>
                      <Select v-model="field.type" @update:model-value="onTypeChange(field)">
                        <SelectTrigger :id="`field-type-${index}`">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem v-for="type in fieldTypes" :key="type" :value="type">
                            {{ type }}
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-9 w-9 mt-7"
                    @click="removeField(index)"
                  >
                    <Icon name="Trash" :size="16" />
                  </Button>
                </div>

                <!-- Collection Dropdown (for reference type) -->
                <div v-if="field.type === 'reference'" class="space-y-2">
                  <Label :for="`field-collection-${index}`">Target Collection</Label>
                  <Select v-model="field.collection" @update:model-value="updateField">
                    <SelectTrigger :id="`field-collection-${index}`">
                      <SelectValue placeholder="Select a collection" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem
                        v-for="col in collectionsStore.collections"
                        :key="col.name"
                        :value="col.name"
                      >
                        {{ col.label }} ({{ col.name }})
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p class="text-xs text-muted-foreground">
                    Records will store a reference (UUID) to a record in this collection
                  </p>
                </div>

                <!-- Checkboxes Row -->
                <div class="flex flex-wrap gap-4">
                  <div class="flex items-center space-x-2">
                    <Checkbox
                      :id="`field-required-${index}`"
                      :model-value="field.required"
                      @update:model-value="
                        (v) => {
                          field.required = !!v;
                          updateField();
                        }
                      "
                    />
                    <Label :for="`field-required-${index}`" class="text-sm font-normal">
                      Required
                    </Label>
                  </div>
                  <div v-if="supportsUnique(field.type)" class="flex items-center space-x-2">
                    <Checkbox
                      :id="`field-unique-${index}`"
                      :model-value="field.unique"
                      @update:model-value="
                        (v) => {
                          field.unique = !!v;
                          updateField();
                        }
                      "
                    />
                    <Label :for="`field-unique-${index}`" class="text-sm font-normal">
                      Unique
                    </Label>
                  </div>
                </div>

                <!-- String-specific constraints -->
                <div v-if="field.type === 'string'" class="grid gap-3 sm:grid-cols-3">
                  <div class="space-y-2">
                    <Label :for="`field-min-length-${index}`" class="text-xs text-muted-foreground">
                      Min Length
                    </Label>
                    <Input
                      :id="`field-min-length-${index}`"
                      v-model.number="field.min_length"
                      type="number"
                      min="0"
                      placeholder="0"
                      class="text-sm"
                      @input="updateField"
                    />
                  </div>
                  <div class="space-y-2">
                    <Label :for="`field-max-length-${index}`" class="text-xs text-muted-foreground">
                      Max Length
                    </Label>
                    <Input
                      :id="`field-max-length-${index}`"
                      v-model.number="field.max_length"
                      type="number"
                      min="0"
                      placeholder="255"
                      class="text-sm"
                      @input="updateField"
                    />
                  </div>
                  <div class="space-y-2">
                    <Label :for="`field-pattern-${index}`" class="text-xs text-muted-foreground">
                      Pattern (Regex)
                    </Label>
                    <Input
                      :id="`field-pattern-${index}`"
                      v-model="field.pattern"
                      placeholder="^[a-z]+$"
                      class="text-sm font-mono"
                      @input="updateField"
                    />
                  </div>
                </div>

                <!-- Numeric constraints -->
                <div v-if="isNumericType(field.type)" class="grid gap-3 sm:grid-cols-2">
                  <div class="space-y-2">
                    <Label :for="`field-min-${index}`" class="text-xs text-muted-foreground">
                      Min Value
                    </Label>
                    <Input
                      :id="`field-min-${index}`"
                      v-model.number="field.min"
                      type="number"
                      placeholder="0"
                      class="text-sm"
                      @input="updateField"
                    />
                  </div>
                  <div class="space-y-2">
                    <Label :for="`field-max-${index}`" class="text-xs text-muted-foreground">
                      Max Value
                    </Label>
                    <Input
                      :id="`field-max-${index}`"
                      v-model.number="field.max"
                      type="number"
                      placeholder="100"
                      class="text-sm"
                      @input="updateField"
                    />
                  </div>
                </div>

                <!-- Default value -->
                <div class="space-y-2">
                  <Label :for="`field-default-${index}`" class="text-xs text-muted-foreground">
                    Default Value (optional)
                  </Label>
                  <Input
                    v-if="field.type === 'string' || field.type === 'reference'"
                    :id="`field-default-${index}`"
                    v-model="field.default"
                    placeholder="Default text value"
                    class="text-sm"
                    @input="updateField"
                  />
                  <Input
                    v-else-if="isNumericType(field.type)"
                    :id="`field-default-${index}`"
                    v-model.number="field.default"
                    type="number"
                    placeholder="0"
                    class="text-sm"
                    @input="updateField"
                  />
                  <Select
                    v-else-if="field.type === 'boolean'"
                    :model-value="field.default === true ? 'true' : field.default === false ? 'false' : ''"
                    @update:model-value="
                      (v) => {
                        field.default = v === 'true' ? true : v === 'false' ? false : undefined;
                        updateField();
                      }
                    "
                  >
                    <SelectTrigger :id="`field-default-${index}`">
                      <SelectValue placeholder="No default" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">No default</SelectItem>
                      <SelectItem value="true">true</SelectItem>
                      <SelectItem value="false">false</SelectItem>
                    </SelectContent>
                  </Select>
                  <p v-else class="text-xs text-muted-foreground italic">
                    Default values for {{ field.type }} type should be set in JSON mode
                  </p>
                </div>

                <!-- Description -->
                <div class="space-y-2">
                  <Label :for="`field-description-${index}`" class="text-xs text-muted-foreground">
                    Description (optional)
                  </Label>
                  <Input
                    :id="`field-description-${index}`"
                    v-model="field.description"
                    placeholder="e.g., The title of the item"
                    class="text-sm"
                    @input="updateField"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Button variant="outline" size="sm" class="w-full" @click="addField">
          <Icon name="Plus" :size="16" class="mr-2" />
          Add Field
        </Button>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useToast } from '../composables/useToast';
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
const editorMode = ref<'json' | 'visual'>('visual');
const jsonText = ref(props.modelValue);
const jsonError = ref('');
const visualFields = ref<SchemaField[]>([]);
const fieldErrors = ref<Record<number, string>>({});

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

// Parse visual fields to JSON
function parseVisualToJson() {
  const schema: Schema = {
    fields: visualFields.value.filter((f) => f.name.trim() !== ''),
  };
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

const fieldTypes = ['string', 'number', 'boolean', 'object', 'array', 'date'];

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
                      <Select v-model="field.type" @update:model-value="updateField">
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
                  <div class="flex items-center space-x-2">
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

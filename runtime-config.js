export const RUNTIME_CONFIG_SCHEMA_VERSION = 1;

const CONFIG_KEYS = Object.freeze([
  'schema_version',
  'memory_budget_gib',
  'batch_size',
  'sequence_length',
  'gradient_accumulation_steps',
  'training_authorized',
  'remote_execution_enabled'
]);

function requireIntegerInRange(name, value, minimum, maximum) {
  if (!Number.isInteger(value)) {
    throw new TypeError(name + ' must be an integer');
  }
  if (value < minimum || value > maximum) {
    throw new RangeError(name + ' must be in [' + minimum + ', ' + maximum + ']');
  }
}

export function validateRuntimeConfig(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('runtime config must be an object');
  }
  const keys = Object.keys(value);
  if (keys.length !== CONFIG_KEYS.length || CONFIG_KEYS.some(key => !Object.hasOwn(value, key))) {
    throw new TypeError('runtime config keys do not match schema version 1');
  }

  requireIntegerInRange('schema_version', value.schema_version, RUNTIME_CONFIG_SCHEMA_VERSION, RUNTIME_CONFIG_SCHEMA_VERSION);
  requireIntegerInRange('memory_budget_gib', value.memory_budget_gib, 2, 10);
  requireIntegerInRange('batch_size', value.batch_size, 1, 16);
  requireIntegerInRange('sequence_length', value.sequence_length, 2, 2048);
  requireIntegerInRange('gradient_accumulation_steps', value.gradient_accumulation_steps, 1, 128);
  if (value.training_authorized !== false) {
    throw new TypeError('runtime config cannot authorize training');
  }
  if (value.remote_execution_enabled !== false) {
    throw new TypeError('runtime config cannot enable remote execution');
  }

  return {
    schema_version: value.schema_version,
    memory_budget_gib: value.memory_budget_gib,
    batch_size: value.batch_size,
    sequence_length: value.sequence_length,
    gradient_accumulation_steps: value.gradient_accumulation_steps,
    training_authorized: false,
    remote_execution_enabled: false
  };
}

export function createRuntimeConfig(memoryBudgetGib) {
  return validateRuntimeConfig({
    schema_version: RUNTIME_CONFIG_SCHEMA_VERSION,
    memory_budget_gib: memoryBudgetGib,
    batch_size: 1,
    sequence_length: 256,
    gradient_accumulation_steps: 1,
    training_authorized: false,
    remote_execution_enabled: false
  });
}

export function serializeRuntimeConfig(value) {
  return JSON.stringify(validateRuntimeConfig(value), null, 2) + '\n';
}

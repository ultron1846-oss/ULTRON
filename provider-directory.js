const PROVIDER_KEYS = Object.freeze([
  'id', 'name', 'role', 'description', 'url', 'status', 'execution_enabled'
]);

function boundedText(value, field, maxLength) {
  if (typeof value !== 'string' || !value.trim() || value.length > maxLength || /[\u0000-\u001f\u007f]/.test(value)) {
    throw new TypeError('Provider ' + field + ' must be a non-empty string of at most ' + maxLength + ' characters.');
  }
  return value.trim();
}

function validateProvider(value, index) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Provider entry ' + index + ' must be an object.');
  }
  if (Object.keys(value).length !== PROVIDER_KEYS.length ||
      PROVIDER_KEYS.some(key => !Object.hasOwn(value, key))) {
    throw new TypeError('Provider entry ' + index + ' does not match the provider schema.');
  }
  if (value.execution_enabled !== false) {
    throw new TypeError('Provider execution must remain disabled in the public directory.');
  }
  const id = boundedText(value.id, 'id', 64);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) throw new TypeError('Provider id format is invalid.');
  let url;
  try {
    url = new URL(boundedText(value.url, 'url', 500));
  } catch {
    throw new TypeError('Provider URL must be a valid HTTPS URL.');
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.port) {
    throw new TypeError('Provider URL must use HTTPS and contain no embedded credentials or custom port.');
  }
  return Object.freeze({
    id,
    name: boundedText(value.name, 'name', 100),
    role: boundedText(value.role, 'role', 300),
    description: boundedText(value.description, 'description', 1_000),
    url: url.href,
    status: boundedText(value.status, 'status', 100),
    execution_enabled: false
  });
}

export function validateProviderDirectory(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new TypeError('Provider directory must be an object.');
  }
  if (value.schema_version !== 1) throw new TypeError('Unsupported provider directory schema version.');
  if (typeof value.purpose !== 'string' || value.purpose.length > 300) {
    throw new TypeError('Provider directory purpose is invalid.');
  }
  if (!Array.isArray(value.providers) || value.providers.length > 50) {
    throw new TypeError('Provider directory providers must be an array of at most 50 entries.');
  }
  const providers = value.providers.map(validateProvider);
  const ids = providers.map(provider => provider.id);
  if (new Set(ids).size !== ids.length) throw new TypeError('Provider directory contains duplicate provider IDs.');
  return Object.freeze({
    schema_version: 1,
    purpose: value.purpose,
    providers: Object.freeze(providers)
  });
}

/**
 * i18n stub — returns the key string as-is.
 * God's Eye View uses a full i18n system; this shim keeps the
 * GLSL shader modules compiling without the translation runtime.
 */
export function msg(key) {
  return key;
}

export default { msg };

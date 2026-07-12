/**
 * @deprecated Since T45 — use `./agent.ts`.
 *
 * Kept as a re-export shim to preserve existing imports
 * (`from '../../types/agentLooper'`) during the migration. New code should
 * import from `./agent.ts` directly. This file will be removed after all
 * consumers have migrated (see .blueprint/tasks/45-naming-migration.md).
 */
export * from './agent';

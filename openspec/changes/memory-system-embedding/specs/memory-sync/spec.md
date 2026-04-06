## ADDED Requirements

### Requirement: Implement sync queue for offline support
The system SHALL maintain a sync queue to handle offline writes and synchronization.

#### Scenario: Queue write operations
- **WHEN** a memory is created/updated/deleted on the client
- **THEN** it SHALL be written to IndexedDB immediately
- **AND** a sync operation SHALL be added to the queue

#### Scenario: Sync operation types
- **WHEN** operations are queued
- **THEN** they SHALL be typed as SAVE, UPDATE, or DELETE
- **AND** each operation SHALL include the memory data and timestamp

#### Scenario: Queue persistence
- **WHEN** the application closes
- **THEN** pending operations SHALL persist in IndexedDB
- **AND** they SHALL be processed on next startup

### Requirement: Implement background sync to server
The system SHALL synchronize client-side changes to the server in the background.

#### Scenario: Flush queue on connectivity
- **WHEN** network is available
- **THEN** the sync manager SHALL periodically flush the queue
- **AND** send operations to the server API

#### Scenario: Batch sync operations
- **WHEN** multiple operations are pending
- **THEN** they MAY be batched for efficiency
- **AND** partial batch failures SHALL be handled individually

#### Scenario: Sync success handling
- **WHEN** an operation syncs successfully
- **THEN** it SHALL be removed from the queue
- **AND** the server state SHALL become authoritative

### Requirement: Handle sync conflicts
The system SHALL handle conflicts when server and client data diverge.

#### Scenario: Timestamp-based conflict resolution
- **WHEN** a conflict is detected (same memory modified on both sides)
- **THEN** the system SHALL use last-write-wins strategy
- **AND** the newer timestamp SHALL prevail

#### Scenario: Conflict detection
- **WHEN** syncing an update
- **THEN** the system SHALL compare server and client timestamps
- **AND** flag conflicts when server version is newer than expected

#### Scenario: Retry with backoff
- **WHEN** a sync operation fails
- **THEN** it SHALL be retried with exponential backoff
- **AND** after 3 failures, it SHALL be marked as failed

### Requirement: Support sync strategies
The system SHALL support different sync strategies based on privacy mode.

#### Scenario: Real-time sync
- **WHEN** sync_strategy is set to "realtime"
- **THEN** changes SHALL sync immediately when online
- **AND** conflicts SHALL be resolved promptly

#### Scenario: Periodic sync
- **WHEN** sync_strategy is set to "periodic" (default)
- **THEN** changes SHALL sync every 5 minutes when online
- **AND** manual sync SHALL be available on demand

#### Scenario: Manual sync
- **WHEN** sync_strategy is set to "manual"
- **THEN** changes SHALL only sync when explicitly requested
- **AND** a sync button SHALL be available in the UI

### Requirement: Privacy mode aware sync
The system SHALL respect privacy mode settings during synchronization.

#### Scenario: Server mode sync
- **WHEN** privacy mode is "server"
- **THEN** all changes SHALL sync to Postgres
- **AND** IndexedDB acts as a cache only

#### Scenario: Local mode (no sync)
- **WHEN** privacy mode is "local"
- **THEN** NO sync operations SHALL be performed
- **AND** memories remain client-side only

#### Scenario: Hybrid mode selective sync
- **WHEN** privacy mode is "hybrid"
- **THEN** non-sensitive memories SHALL sync to server
- **AND** user SHALL be able to mark memories as "local-only"

### Requirement: Provide sync status visibility
The system SHALL provide visibility into sync status.

#### Scenario: Sync state tracking
- **WHEN** sync operations occur
- **THEN** the system SHALL track: pending count, last sync time, sync errors

#### Scenario: Offline indicator
- **WHEN** the client is offline
- **THEN** a visual indicator SHALL show offline status
- **AND** pending operation count SHALL be displayed

#### Scenario: Sync completion notification
- **WHEN** pending operations complete
- **THEN** a brief notification MAY be shown
- **AND** any errors SHALL be logged and surfaced

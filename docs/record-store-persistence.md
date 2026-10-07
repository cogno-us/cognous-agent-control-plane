# Bounded record-store persistence

`BoundedRecordStore` protects each initialization, load and append with an
exclusive Linux `flock` on a stable `<record-name>.lock` sidecar. The lock covers
reload, validation, append, temporary-file flush/fsync, atomic replacement and
parent-directory fsync. Each transaction opens its own descriptor and closes it
on exit; process death releases kernel ownership. The data inode is not the lock
inode. Instances never cache a document for a later mutation.

A successful append retains one new entry for that call and all earlier entries.
It is not an idempotency API: repeating a call after an uncertain result may append
again. Repeated attempt IDs can be legitimate lifecycle transitions and are not
collapsed. Decisions, attempts, observations and reconciliations retain their
original identities and order within each append history.

## Compatibility and supported boundary

- Existing JSON files remain in place and need no migration. Initialization
  validates existing data without rewriting it. Appends preserve raw historical
  fields, including extension fields not exposed by current typed readers.
- All participants must use the repaired implementation, under the same service
  user, with one canonical path in a trusted writable directory. Symlink aliases
  resolve to that path; hard-link aliases and concurrent path/mount replacement
  are unsupported. Stop old writers before upgrading. Old code ignores the lock.
- Linux is required. Mount inspection allows ext2/3/4, XFS, Btrfs, tmpfs and local
  overlay mounts, subject to working flock, atomic same-directory rename and
  file/directory fsync. Qualification was run on Linux in the supplied workspace;
  it is not a filesystem certification. Overlay backing storage must itself meet
  these local semantics. NFS, SMB/CIFS, FUSE and unknown types are rejected.
  Missing mount metadata, unavailable/failed locking and unsupported platforms
  raise errors; there is no thread-only or unlocked fallback.
- Record and sidecar creation use private service-user permissions. Multiple OS
  users sharing a store, remote filesystems and cross-host coordination are not
  supported. Use independently initialized spawned processes; forking while a
  transaction is active can inherit its descriptor/lock and is unsupported.
  tmpfs retains data across process death, not host reboot.
- Never unlink/recreate the sidecar lock while any participant can use the store:
  doing so splits lock ownership. A leftover sidecar is normal, not a stale owner.

## Failure and recovery

Corrupt/malformed/invalid records raise an error and are never replaced by an empty
store. Persistence and lock failures propagate. A unique temporary file alone is
not the concurrency mechanism; complete transaction locking prevents lost updates.

Termination before replacement leaves the previous committed document authoritative.
Termination after replacement leaves a complete new document visible, even if the
caller never received success. Failure of directory fsync after replacement is
also explicit but the append may already be visible: inspect retained history;
do not infer absence or blindly repeat an uncertain append. Uncommitted `.tmp`
files after process death are ignored, never promoted. They may be removed only
with writers stopped. The JSON document remains authoritative.

Tests terminate processes at both sides of real replacement, then require a
separate waiting process to reopen/write within a bounded deadline and retain
prior content. This is process-interruption evidence, not hardware/power-loss
certification. A live process may hold the lock until its transaction finishes;
there is no lock lease or transaction timeout.

## Exclusions

This repair does not change `LocalRefundDestination`, authorization, reconciliation
semantics or any hub pin. There is no atomic transaction across records and a
destination effect, whole-workflow concurrency guarantee, distributed budget or
exactly-once delivery claim. Hub adoption requires separate reviewed qualification.

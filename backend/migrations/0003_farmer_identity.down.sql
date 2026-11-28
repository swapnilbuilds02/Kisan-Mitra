-- Disposable test rollback only. Does not delete farmer records.
BEGIN;
DROP FUNCTION km_private.claim_farmer(TEXT);
DROP FUNCTION km_private.prepare_farmer(TEXT, UUID, TEXT);
COMMIT;

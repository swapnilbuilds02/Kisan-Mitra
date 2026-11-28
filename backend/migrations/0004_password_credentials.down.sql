BEGIN;
DROP FUNCTION km_private.set_password_credential(UUID,TEXT,BOOLEAN);
DROP FUNCTION km_private.read_password_credential(UUID);
DROP FUNCTION km_private.password_login_attempt(TEXT,TEXT);
DROP TABLE km_private.password_login_limits;
DROP TABLE km_private.password_credentials;
COMMIT;

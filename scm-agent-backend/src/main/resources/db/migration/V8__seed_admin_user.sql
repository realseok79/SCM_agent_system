-- db/migration/V8__seed_admin_user.sql
INSERT INTO users (username, email, password, role)
VALUES ('admin', 'admin@sigma.com', '$2a$10$eFytJDGtjbThXa5zF14gE.9qQ3yvXWkU8zN2wV4rE1zD0vG.i3W7.', 'ROLE_ADMIN')
ON CONFLICT (username) DO NOTHING;

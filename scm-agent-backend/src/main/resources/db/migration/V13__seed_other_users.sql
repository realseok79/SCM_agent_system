-- db/migration/V13__seed_other_users.sql
INSERT INTO users (username, email, password, role)
VALUES ('logistics', 'logistics@sigma.com', '$2b$12$E5rq94xexGvM4TxpPJ9aNuA34yT6Hv98.N8euwpR4v6fcrwe19D1O', 'ROLE_LOGISTICS')
ON CONFLICT (username) DO NOTHING;

INSERT INTO users (username, email, password, role)
VALUES ('executive', 'executive@sigma.com', '$2b$12$ssur3XKckIwCdyP/KoVwqeHIXwNAHtGDYEwWgSbA9mBf7zfTPiB2C', 'ROLE_EXECUTIVE')
ON CONFLICT (username) DO NOTHING;

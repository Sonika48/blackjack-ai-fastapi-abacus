CREATE TABLE IF NOT EXISTS abacus (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    total NUMERIC NOT NULL CHECK (total = trunc(total))
);
INSERT INTO abacus (id, total) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;

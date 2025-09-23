CREATE TABLE IF NOT EXISTS people (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);

INSERT INTO people (name) VALUES
  ('Alice'),
  ('Bob'),
  ('Charlie');
